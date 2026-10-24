import pytest

from app import main


class FakeChatClient:
    """Stands in for Gemma: returns `reply`, or raises it if it's an exception, and records prompts."""

    def __init__(self, reply=None):
        self.reply = reply if reply is not None else {"headline": "Fake headline", "body": "Fake body."}
        self.prompts: list[str] = []

    async def chat_json(self, system, user, schema):
        self.prompts.append(user)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture(autouse=True)
def fake_gemma(monkeypatch):
    """Keep every test away from the real Ollama server."""
    fake = FakeChatClient()
    monkeypatch.setattr(main.worker, "client", fake)
    return fake
