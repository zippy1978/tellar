import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import logging
import time
from urllib.parse import urlparse
from fastapi.responses import StreamingResponse
import uvicorn
import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from tellar.server.discovery import Discovery
from tellar.server.model import Info, Message
from tellar.character import Answer, Character
import websockets
import requests


# Logger
logger = logging.getLogger(__name__)


def __find_free_port(
    start_port: int = 8000, socket_kind: socket.SocketKind = socket.SOCK_STREAM
) -> int:
    """Find a free port starting from `start_port`."""
    with socket.socket(socket.AF_INET, socket_kind) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for port in range(start_port, start_port + 100):  # Check a range of ports
            try:
                s.bind(("0.0.0.0", port))
                s.close()
                return port
            except OSError:
                # Port is already in use, try the next one
                continue
    raise RuntimeError("No free ports available")


class AppState:
    def __init__(self, char):
        self.char = char
        # Holds conversations from different users
        self.conversations_from = {}
        # Holds history of conversations from different users
        self.history_from = {}
        self.picture = None
        self.description = None


def create_app(char: Character, discovery: Discovery) -> FastAPI:

    app = FastAPI()
    state = AppState(char)

    @app.get("/")
    async def read_root():
        return Info(name=char.name).to_json()

    @app.get("/picture")
    async def read_picture():
        if state.picture is None:
            answer = await state.char.clone().answer(
                "Draw the most accurate portrait picture of you based on the information from story_tool. Use a picture style matching the era and universe of your story."
            )
            logger.info(f"Picture: {answer.image}")
            state.picture = requests.get(answer.image).content

        return StreamingResponse(BytesIO(state.picture), media_type="image/jpeg")

    @app.get("/description")
    async def read_description():
        if state.description is None:
            answer = await state.char.clone().answer(
                "Describe yourself in a few words (no full sentence)."
            )
            logger.info(f"Description: {answer.text}")
            state.description = answer.text
        return state.description

    @app.get("/history/{char_name}")
    async def read_history(char_name: str):
        if char_name not in state.conversations_from:
            return []
        return [msg.to_json() for msg in state.history_from[char_name]]

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        try:
            await websocket.accept()
            while True:
                data = await websocket.receive_json()
                msg = Message.from_json(data)
                msg.timestamp = int(time.time())
                if msg.sender not in state.conversations_from:
                    logger.info(f"New conversation from [{msg.sender}]")
                    state.conversations_from[msg.sender] = state.char.clone()
                    state.history_from[msg.sender] = []
                logger.info(f"Received message from [{msg.sender}]: {msg.text}")
                state.history_from[msg.sender].append(msg)
                answer = await state.conversations_from[msg.sender].answer(msg.text)
                logger.info(f"Answer: {answer.text} [{answer.image}]")
                # Convert answer to Message model
                reply_message = Message(
                    sender=char.name,
                    text=answer.text,
                    timestamp=int(time.time()),
                    image=answer.image,
                )
                state.history_from[msg.sender].append(reply_message)
                await websocket.send_json(reply_message.to_json())
        except WebSocketDisconnect as e:
            logger.info(f"Client disconnected: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")
            await websocket.close()

    # Preload description
    asyncio.run(read_description())
    
    return app


async def __start_conversation(discovery: Discovery, char: Character):

    # Wait for other servers to appear
    while not discovery.servers:
        # Wait 1 second
        await asyncio.sleep(1)

    # Find first server in discovery that has server.info.name diffetent from char.name
    server = next(
        (
            s
            for s in discovery.servers
            if s.info is not None and s.info.name != char.name
        ),
        None,
    )
    if server is None:
        logger.error("Nobody to talk to...")
        return

    logger.info(f"Talking to {server.info.name}")

    # Prepare URI
    url = urlparse(server.url)
    ws_url = f"ws://{url.netloc}/ws"

    # Generate goal
    goal = await char.clone(language="english").answer(
        "What is your main goal in life (write it at 3rd person) ?"
    )
    logger.info(f"Goal: {goal.text}")

    # Generate intial message
    initial_msg = await char.clone().answer(
        "What would you say to someone you just met to engage the conversation ? (say it as like you speak to this person)"
    )

    # Clone character with new goal
    char = char.clone(
        goal=f"You are talking to {server.info.name}. Check if you know him/her. Try to follow your goal: {goal.text}"
    )

    retries = 0
    while True:
        try:
            async with websockets.connect(ws_url) as websocket:
                if retries > 0:
                    initial_msg = Message(
                        sender=char.name, text="?", timestamp=int(time.time())
                    )
                await websocket.send(
                    json.dumps(
                        Message(
                            sender=char.name,
                            text=initial_msg.text,
                            timestamp=int(time.time()),
                        ).to_json()
                    )
                )
                logger.info(f"## YOU >> {initial_msg.text}")
                while True:
                    try:
                        data = await websocket.recv()
                        answer = Answer.from_json(json.loads(data))
                        logger.info(
                            f"## {server.info.name} >> {answer.text} [{answer.image}]"
                        )
                        next_msg = await char.answer(answer.text)
                        logger.info(f"## YOU >> {next_msg.text}")
                        await websocket.send(
                            json.dumps(
                                Message(
                                    sender=char.name,
                                    text=next_msg.text,
                                    timestamp=int(time.time()),
                                ).to_json()
                            )
                        )
                        print(f"history len : {len(char.chat_history)}")
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"Connection closed: {e}")
                        break
        except (websockets.exceptions.ConnectionClosed, Exception) as e:
            logger.error(f"Connection error: {e}")

        # Wait before retrying to avoid rapid continuous reconnections
        await asyncio.sleep(5)
        retries += 1


def start_server(char: Character):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor = ThreadPoolExecutor()

    logger.info(f"Starting server for {char.name}")

    http_port = __find_free_port()
    udp_port = __find_free_port(start_port=9000, socket_kind=socket.SOCK_DGRAM)

    discovery = Discovery(udp_port, http_port)
    discovery.start()

    # If char.name is "Hermione"
    if char.name == "Hermione":
        loop.run_in_executor(
            executor, loop.run_until_complete, __start_conversation(discovery, char)
        )

    app = create_app(char, discovery)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=http_port,
        log_level="info",
        ws_ping_interval=50,
        ws_ping_timeout=50,
    )

    discovery.stop()
