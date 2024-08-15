import socket
import unittest
from unittest.mock import Mock, patch
from tellar.server.discovery import Discovery
from tellar.server.model import Info


class TestDiscovery(unittest.TestCase):

    def setUp(self):
        self.discovery = Discovery(udp_port=9000, http_port=8000)

    def test_init(self):
        self.assertEqual(self.discovery.udp_port, 9000)
        self.assertEqual(self.discovery.http_port, 8000)
        self.assertFalse(self.discovery._Discovery__running)
        self.assertEqual(self.discovery.servers, set())

    @patch("threading.Timer")
    @patch("threading.Thread")
    def test_start(self, mock_thread, mock_timer):
        self.discovery.start()
        self.assertTrue(self.discovery._Discovery__running)
        mock_timer.assert_called_once()
        mock_thread.assert_called_once()

    @patch("threading.Timer")
    @patch("threading.Thread")
    def test_stop(self, mock_thread, mock_timer):
        self.discovery._Discovery__running = True
        self.discovery._Discovery__discovery_timer = mock_timer.return_value
        self.discovery._Discovery__adv_thread = mock_thread.return_value

        self.discovery.stop()

        self.assertFalse(self.discovery._Discovery__running)
        mock_timer.return_value.join.assert_called_once()
        mock_timer.return_value.cancel.assert_called_once()
        mock_thread.return_value.join.assert_called_once()

    @patch("socket.socket")
    @patch("requests.get")
    @patch("tellar.server.discovery.range")
    @patch("threading.Timer")
    def test_discover(self, mock_timer, mock_range, mock_get, mock_socket):
        # Set up the range mock to only iterate once
        mock_range.return_value = range(9000, 9001)

        mock_socket_instance = mock_socket.return_value.__enter__.return_value
        mock_socket_instance.recvfrom.side_effect = [
            (b"http://test.com", ("127.0.0.1", 9000)),
            socket.timeout,  # Simulate a timeout to exit the inner while loop
        ]
        mock_get.return_value.json.return_value = {"name": "Test Server"}
        mock_get.return_value.raise_for_status = Mock()

        self.discovery._Discovery__running = True

        # Directly call the __discover method
        self.discovery._Discovery__discover()

        # Stop the discovery process
        self.discovery._Discovery__running = False

        # Check the results
        self.assertEqual(len(self.discovery.servers), 1)
        server = list(self.discovery.servers)[0]
        self.assertEqual(server.url, "http://test.com")
        self.assertIsInstance(server.info, Info)

    @patch("socket.socket")
    @patch("socket.gethostbyname")
    def test_advertise(self, mock_gethostbyname, mock_socket):
        mock_gethostbyname.return_value = "192.168.1.100"
        mock_socket_instance = mock_socket.return_value.__enter__.return_value

        # Set up the mock to raise an exception after sending the response
        mock_socket_instance.recvfrom.side_effect = [
            (b"TELLAR_SERVER", ("127.0.0.1", 9000)),
            Exception("Stop the loop"),
        ]

        self.discovery._Discovery__running = True

        # Run the advertise method in a separate thread with a timeout
        import threading
        import time

        def run_advertise():
            try:
                self.discovery._Discovery__advertise(9000, 8000)
            except Exception:
                pass  # Expected exception to stop the loop

        advertise_thread = threading.Thread(target=run_advertise)
        advertise_thread.start()

        # Wait for a short time to allow the method to process
        time.sleep(0.1)

        # Stop the discovery process
        self.discovery._Discovery__running = False

        # Wait for the thread to finish with a timeout
        advertise_thread.join(timeout=1)

        # Check if the correct response was sent
        mock_socket_instance.sendto.assert_any_call(
            b"http://192.168.1.100:8000", ("127.0.0.1", 9000)
        )

        # Ensure the thread has finished
        self.assertFalse(advertise_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
