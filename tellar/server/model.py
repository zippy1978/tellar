from typing import Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    sender: str
    text: str
    timestamp: int
    image: Optional[str] = None

    def to_json(self):
        return {"sender": self.sender, "text": self.text, "timestamp": self.timestamp, "image": self.image}

    @classmethod
    def from_json(cls, json):
        return cls(
            sender=json.get("sender", ""),
            text=json.get("text", ""),
            timestamp=json.get("timestamp", 0),
            image=json.get("image")
        )


class Info(BaseModel):
    name: str

    def to_json(self):
        return {"name": self.name}

    @classmethod
    def from_json(cls, json):
        return cls(name=json.get("name", None))