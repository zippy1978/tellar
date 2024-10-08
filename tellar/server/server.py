import asyncio
import hashlib
from io import BytesIO
import logging
import time
from fastapi.responses import StreamingResponse
import requests
import uvicorn
import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from tellar.server.discovery import Discovery
from tellar.server.model import Info, Message
from tellar.character import Character

from tellar.utils.network_utils import find_free_port, get_ip


# Logger
logger = logging.getLogger(__name__)


class Server:
    class AppState:
        def __init__(self):
            self.conversations_from = {}
            self.history_from = {}
            self.picture = None
            self.description = None
            self.images = {}
            self.lock = asyncio.Lock()
  
    def __init__(self, char: Character):
        self.__char = char
        self.__state = Server.AppState()
        self.__http_port = None
        self.__udp_port = None
        self.__app = self.__create_app()

    async def __http_get(self, url: str) -> requests.Response:
        response = await asyncio.to_thread(requests.get, url)
        return response

    def __handle_new_conversation(self, msg: Message):
        logger.info(f"New conversation from [{msg.sender}]")
        self.__state.conversations_from[msg.sender] = self.__char.clone()
        self.__state.history_from[msg.sender] = []

    async def __get_cached_image(self, image_url: str) -> str:
        if image_url is None:
            return None
        # Genrerate image hash from url
        image_hash = hashlib.sha256(image_url.encode()).hexdigest()
        # Store it to cache if not present
        if image_hash not in self.__state.images:
            async with self.__state.lock:
                if image_hash not in self.__state.images:
                    response = await self.__http_get(image_url)
                    self.__state.images[image_hash] = response.content
        # Retrieve local server address
        return f"http://{get_ip()}:{self.__http_port}/image/{image_hash}"

    async def __handle_new_message(self, msg: Message) -> Message:
        logger.info(f"Received message from [{msg.sender}]: {msg.text}")
        self.__state.history_from[msg.sender].append(msg)
        answer = await self.__state.conversations_from[msg.sender].answer(msg.text)
        logger.info(f"Answer: {answer.text} [{answer.image}]")
        # Convert answer to Message model
        reply_message = Message(
            sender=self.__char.name,
            text=answer.text,
            timestamp=int(time.time()),
            image=await self.__get_cached_image(answer.image),
        )
        self.__state.history_from[msg.sender].append(reply_message)
        return reply_message

    def __create_app(self) -> FastAPI:

        app = FastAPI()

        @app.get("/")
        async def read_root():
            return Info(name=self.__char.name).to_json()

        @app.get("/picture")
        async def read_picture():
            if self.__state.picture is None:
                async with self.__state.lock:
                    if self.__state.picture is None:
                        answer = await self.__char.clone().answer(
                            "Draw the most accurate portrait picture of you based on the information from story_tool. Use a picture style matching the era and universe of your story."
                        )
                        logger.info(f"Picture: {answer.image}")
                        response = await self.__http_get(answer.image)
                        self.__state.picture = response.content

            return StreamingResponse(
                BytesIO(self.__state.picture), media_type="image/jpeg"
            )

        @app.get("/image/{hash}")
        async def read_image(hash: str):
            return StreamingResponse(
                BytesIO(self.__state.images[hash]), media_type="image/jpeg"
            )

        @app.get("/description")
        async def read_description():
            if self.__state.description is None:
                async with self.__state.lock:
                    if self.__state.description is None:
                        answer = await self.__char.clone().answer(
                            "Describe yourself in a few words (no full sentence)."
                        )
                        logger.info(f"Description: {answer.text}")
                        self.__state.description = answer.text
            return self.__state.description

        @app.get("/history/{char_name}")
        async def read_history(char_name: str):
            if char_name not in self.__state.conversations_from:
                return []
            return [msg.to_json() for msg in self.__state.history_from[char_name]]

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_json()

                    # Decode message
                    msg = Message.from_json(data)
                    msg.timestamp = int(time.time())

                    # Handle new conversation
                    if msg.sender not in self.__state.conversations_from:
                        self.__handle_new_conversation(msg)

                    # Handle message
                    reply_message = await self.__handle_new_message(msg)

                    # Send reply
                    await websocket.send_json(reply_message.to_json())

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error in WebSocket handler: {str(e)}")
                await websocket.close(code=1011)  # Internal error


        return app

    def start(self):

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        logger.info(f"Starting server for {self.__char.name}")

        self.__http_port = find_free_port()
        self.__udp_port = find_free_port(start_port=9000, socket_kind=socket.SOCK_DGRAM)

        discovery = Discovery(self.__udp_port, self.__http_port)
        discovery.start()

        uvicorn.run(
            self.__app,
            host="0.0.0.0",
            port=self.__http_port,
            log_level="info",
            ws_ping_interval=50,
            ws_ping_timeout=50,
        )

        discovery.stop()
