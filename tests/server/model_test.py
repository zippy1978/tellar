import unittest
from tellar.server.model import Message, Info

class TestModel(unittest.TestCase):
    def test_message(self):
        msg = Message(sender="Alice", text="Hello", timestamp=1234567890, image="image.jpg")
        json_data = msg.to_json()
        self.assertEqual(json_data, {"sender": "Alice", "text": "Hello", "timestamp": 1234567890, "image": "image.jpg"})
        
        reconstructed_msg = Message.from_json(json_data)
        self.assertEqual(reconstructed_msg, msg)

    def test_info(self):
        info = Info(name="Test Bot")
        json_data = info.to_json()
        self.assertEqual(json_data, {"name": "Test Bot"})
        
        reconstructed_info = Info.from_json(json_data)
        self.assertEqual(reconstructed_info, info)

    def test_message_without_image(self):
        msg = Message(sender="Bob", text="Hi", timestamp=1234567890)
        json_data = msg.to_json()
        self.assertEqual(json_data, {"sender": "Bob", "text": "Hi", "timestamp": 1234567890, "image": None})

    def test_from_json_with_missing_fields(self):
        json_data = {"sender": "Charlie"}
        msg = Message.from_json(json_data)
        self.assertEqual(msg.sender, "Charlie")
        self.assertEqual(msg.text, "")
        self.assertEqual(msg.timestamp, 0)
        self.assertIsNone(msg.image)

if __name__ == '__main__':
    unittest.main()