from typing import Optional
from pydantic import BaseModel


class Message(BaseModel):
    sender: str
    text: str
    image: Optional[str] = None

    def to_json(self):
        return {"sender": self.sender, "text": self.text, "image": self.image}

    @classmethod
    def from_json(cls, json):
        return cls(sender=json.get("sender", None), text=json.get("text", None), image=json.get("image", None))


class Info(BaseModel):
    name: str

    def to_json(self):
        return {"name": self.name}

    @classmethod
    def from_json(cls, json):
        return cls(name=json.get("name", None))
