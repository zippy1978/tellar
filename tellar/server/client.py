import asyncio
import json
import logging
import socket
import time
from urllib.parse import urlparse

from colorama import Fore, Style
from tellar.server.discovery import Discovery
from tellar.server.model import Message
from tellar.character import Answer, Character
import websockets

from tellar.utils.network_utils import find_free_port

# Logger
logger = logging.getLogger(__name__)


class Client:
    def __init__(self, char: Character):
        self.__char = char

    async def astart(self):
        http_port = find_free_port()
        udp_port = find_free_port(start_port=9000, socket_kind=socket.SOCK_DGRAM)

        discovery = Discovery(udp_port, http_port)
        discovery.start()

        # Wait for other servers to appear
        while not discovery.servers:
            # Wait 1 second
            time.sleep(1)

        # Find first server in discovery that has server.info.name diffetent from char.name
        server = next(
            (
                s
                for s in discovery.servers
                if s.info is not None and s.info.name != self.__char.name
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
        goal = await self.__char.clone(language="english").answer(
            "What is your main goal in life (write it at 3rd person) ?"
        )
        logger.info(f"Goal: {goal.text}")

        # Generate intial message
        initial_msg = await self.__char.clone().answer(
            "What would you say to someone you just met to engage the conversation ? (say it as like you speak to this person)"
        )

        # Clone character with new goal
        char = self.__char.clone(
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

                    logger.info(
                        Style.BRIGHT
                        + Fore.BLUE
                        + char.name
                        + " > "
                        + Style.RESET_ALL
                        + initial_msg.text
                    )
                    while True:
                        try:
                            data = await websocket.recv()
                            answer = Answer.from_json(json.loads(data))
                            logger.info(
                                Style.BRIGHT
                                + Fore.GREEN
                                + server.info.name
                                + " > "
                                + Style.RESET_ALL
                                + answer.text
                                + " ["
                                + (answer.image or "no image")
                                + "]"
                            )

                            next_msg = await char.answer(answer.text)
                            logger.info(
                                Style.BRIGHT
                                + Fore.BLUE
                                + char.name
                                + " > "
                                + Style.RESET_ALL
                                + next_msg.text
                            )
                            await websocket.send(
                                json.dumps(
                                    Message(
                                        sender=char.name,
                                        text=next_msg.text,
                                        timestamp=int(time.time()),
                                    ).to_json()
                                )
                            )
                        except websockets.exceptions.ConnectionClosed as e:
                            logger.error(f"Connection closed: {e}")
                            break
            except (websockets.exceptions.ConnectionClosed, Exception) as e:
                logger.error(f"Connection error: {e}")

            # Wait before retrying to avoid rapid continuous reconnections
            await asyncio.sleep(5)
            retries += 1

    def start(self):
        asyncio.run(self.astart())
