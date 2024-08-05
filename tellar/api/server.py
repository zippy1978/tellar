import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from urllib.parse import urlparse
import uvicorn
import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from tellar.api.discovery import Discovery
from tellar.api.model import Info, Message
from tellar.character import Answer, Character
import websockets
from time import sleep
from langchain_core.vectorstores.base import VectorStore

# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log format
    handlers=[logging.StreamHandler()],  # Console output
)

# Create a logger instance
logger = logging.getLogger("uvicorn.error")
# Add filter to remove requests logs
logger.addFilter(lambda record: "requests.packages.urllib3.connectionpool" not in record.getMessage())


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


def __create_app(char: Character, discovery: Discovery) -> FastAPI:

    app = FastAPI()
    
    # Holds conversations from different users
    conversations_from = {}

    @app.get("/")
    async def read_root():
        return Info(name=char.name).to_json()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        try:
            await websocket.accept()
            while True:
                data = await websocket.receive_json()
                msg = Message.from_json(data)
                if msg.sender not in conversations_from:
                    logger.info(f"New conversation from [{msg.sender}]")
                    conversations_from[msg.sender] = char.clone()
                logger.info(f"Received message from [{msg.sender}]: {msg.text}")
                answer = conversations_from[msg.sender].answer(msg.text)
                logger.info(f"Answer: {answer.text} [{answer.image}]")
                await websocket.send_json(answer.to_json())
        except WebSocketDisconnect as e:
            logger.info(f"Client disconnected: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")

    return app

async def __start_conversation(discovery: Discovery, char: Character):
    
    # Wait for other servers to appear
    while not discovery.servers:
            # Wait 1 second
            await asyncio.sleep(1)
            
    # Find first server in discovery that has server.info.name diffetent from char.name
    server = next((s for s in discovery.servers if s.info is not None and s.info.name != char.name), None)
    if server is None:
        logger.error("Nobody to talk to...")
        return
        
    logger.info(f"Talking to {server.info.name}")
    
    # Prepare URI
    url = urlparse(server.url)
    ws_url = f"ws://{url.netloc}/ws"
    
    # Generate goal
    goal = char.clone(language="english").answer("What is your main goal in life (write it at 3rd person) ?")
    logger.info(f"Goal: {goal.text}")
    
    # Generate intial message
    initial_msg = char.clone().answer("What would you say to someone you just met to engage the conversation ? (say it as like you speak to this person)")
    
    # Clone character with new goal
    char = char.clone(goal=f"You are talking to {server.info.name}. Check if you know him/her. Try to follow your goal: {goal.text}")
    
    retries = 0
    while True:
        try:
            async with websockets.connect(ws_url) as websocket:
                if retries > 0:
                    initial_msg = Message(sender=char.name, text="?")
                await websocket.send(json.dumps(Message(sender=char.name, text=initial_msg.text).to_json()))
                logger.info(f"## YOU >> {initial_msg.text}")
                while True:
                    try:
                        data = await websocket.recv()
                        answer = Answer.from_json(json.loads(data))
                        logger.info(f"## {server.info.name} >> {answer.text} [{answer.image}]")
                        next_msg = char.answer(answer.text)
                        logger.info(f"## YOU >> {next_msg.text}")
                        await websocket.send(json.dumps(Message(sender=char.name, text=next_msg.text).to_json()))
                        print(f"history len : {len(char.chat_history)}")
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"Connection closed: {e}")
                        break
        except (websockets.exceptions.ConnectionClosed, Exception) as e:
            logger.error(f"Connection error: {e}")
            
        # Wait before retrying to avoid rapid continuous reconnections
        await asyncio.sleep(5)
        retries += 1
    
            
    

def start_server(vectordb: VectorStore, character: str, language: str, debug: bool):
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor = ThreadPoolExecutor()

    
    # Create character
    char = Character(
        name=character,
        retriever=vectordb.as_retriever(),
        char_name=character,
        language=language,
        verbose=debug,
    )
    
    logger.info(f"Starting server for {char.name}")

    http_port = __find_free_port()
    udp_port = __find_free_port(start_port=9000, socket_kind=socket.SOCK_DGRAM)

    discovery = Discovery(udp_port, http_port, logger)
    discovery.start()
    
    # If char.name is "Harry"
    if char.name == "Harry":
        loop.run_in_executor(executor, loop.run_until_complete, __start_conversation(discovery, char))

    app = __create_app(char, discovery)

    uvicorn.run(app, host="0.0.0.0", port=http_port, log_level="info", ws_ping_interval=50, ws_ping_timeout=50)

    discovery.stop()
