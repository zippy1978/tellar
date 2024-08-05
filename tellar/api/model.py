from typing import Optional
from pydantic import BaseModel


class Message(BaseModel):
    sender: str
    text: str

    def to_json(self):
        return {"sender": self.sender, "text": self.text}

    @classmethod
    def from_json(cls, json):
        return cls(sender=json.get("sender", None), text=json.get("text", None))


class Info(BaseModel):
    name: str

    def to_json(self):
        return {"name": self.name}

    @classmethod
    def from_json(cls, json):
        return cls(name=json.get("name", None))
