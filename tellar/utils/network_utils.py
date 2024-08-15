import socket

def find_free_port(
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