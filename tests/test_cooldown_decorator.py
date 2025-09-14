import asyncio

import pytest

from bot.cooldowns import cooldown, cooldown_manager


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self.sent = []
        self._done = False

    def is_done(self):
        return self._done

    async def defer(self):
        self.deferred = True
        self._done = True

    async def send_message(self, content, ephemeral=False):
        self.sent.append({"content": content, "ephemeral": ephemeral})


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class FakeCommand:
    def __init__(self, name):
        self.name = name


class FakeInteraction:
    def __init__(self, user_id=1, command_name="test_cmd"):
        self.user = FakeUser(user_id)
        self.command = FakeCommand(command_name)
        self.response = FakeResponse()


@pytest.mark.asyncio
async def test_cooldown_decorator_applies_and_blocks():
    # Reset manager state
    cooldown_manager.reset_user_cooldowns(1)

    called = {"count": 0}

    @cooldown(1)
    async def test_command(interaction):
        called["count"] += 1
        return "ok"

    interaction = FakeInteraction(user_id=1, command_name="test_cmd")

    # First call should execute and defer the interaction
    await test_command(interaction)
    assert called["count"] == 1
    assert interaction.response.deferred is True

    # Second call should be blocked by cooldown
    await test_command(interaction)
    assert len(interaction.response.sent) == 1
    assert "on cooldown" in interaction.response.sent[0]["content"].lower()

    # Wait for cooldown to expire and call again
    await asyncio.sleep(1.1)
    await test_command(interaction)
    assert called["count"] == 2
