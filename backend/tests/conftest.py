import pytest

from app import main
from app.ai.worker import AIWorker


class FakeChatClient:
    """Stands in for Gemma: returns `reply`, or raises it if it's an exception, and records prompts."""

    def __init__(self, reply=None):
        self.reply = reply if reply is not None else {"headline": "Fake headline", "body": "Fake body."}
        self.prompts: list[str] = []
        self.systems: list[str] = []

    async def chat_json(self, system, user, schema):
        self.prompts.append(user)
        self.systems.append(system)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture(autouse=True)
def fake_gemma(monkeypatch):
    """Give each test a fresh worker with a fake client, so no test reaches the real Ollama server."""
    fake = FakeChatClient()
    monkeypatch.setattr(main, "worker", AIWorker(fake))
    return fake
