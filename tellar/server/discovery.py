from dataclasses import dataclass
from logging import Logger
import logging
import requests
import socket
import threading
from tellar.server.model import Info

# Logger
logger = logging.getLogger(__name__)

class Discovery:

    @dataclass
    class Server:
        url: str
        info: Info

        def __eq__(self, other):
            return self.url == other.url

        def __hash__(self):
            return hash(self.url)

    def __init__(self, udp_port: int, http_port: int):
        self.udp_port = udp_port
        self.http_port = http_port
        self.__running = False
        self.servers = set()

    def start(self):
        self.__running = True
        self.__discovery_timer = threading.Timer(1, self.__discover)
        self.__discovery_timer.start()
        self.__adv_thread = threading.Thread(
            target=self.__advertise,
            kwargs={"udp_port": self.udp_port, "http_port": self.http_port},
        )
        self.__adv_thread.start()

    def stop(self):
        self.__running = False
        self.__discovery_timer.join()
        self.__discovery_timer.cancel()
        self.__adv_thread.join()

    def __discover(self):
        logger.debug("Discovering servers...")

        new_servers = set()

        # Try to discover peers on a port range
        for port in range(9000, 9009):

            if self.__running == False:
                break

            with socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            ) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(1)

                # Send broadcast message
                message = "DISCOVER_SERVER"
                sock.sendto(message.encode(), ("<broadcast>", port))

                while self.__running:
                    try:
                        data, addr = sock.recvfrom(1024)
                        new_servers.add(Discovery.Server(url=data.decode(), info=None))
                    except socket.timeout:
                        break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        break

        # Check for disconnected servers
        all_servers = self.servers.union(new_servers)
        servers = set()
        for s in all_servers:
            try:
                response = requests.get(s.url)
                response.raise_for_status()
                s.info = Info.from_json(response.json())
                servers.add(s)
            except Exception as e:
                continue
        self.servers = servers

        logger.debug(f"Discovered servers: {self.servers}")

        # Restart
        if self.__running:
            self.__discovery_timer = threading.Timer(5, self.__discover)
            self.__discovery_timer.start()

    def __advertise(self, udp_port: int, http_port: int):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", udp_port))
            sock.settimeout(3)
            logger.info(f"Server is discoverable on UDP {udp_port}")
            while self.__running:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data.decode() == "DISCOVER_SERVER":
                        response = f"http://{socket.gethostbyname(socket.gethostname())}:{http_port}"
                        sock.sendto(response.encode(), addr)
                        sock.sendto(response.encode(), ("127.0.0.1", udp_port))
                except KeyboardInterrupt:
                    # Allow for graceful exit if Ctrl+C is pressed
                    break
                except socket.timeout:
                    if self.__running == False:
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    break

            logger.info("Server is no more discoverable")
