#!/usr/bin/env python3
"""CLI harness to invoke bot command handlers locally for quick testing.

Usage:
  python scripts/cli_test_commands.py --command ask --question "Hello"
  python scripts/cli_test_commands.py --command summarize --hours 2

This creates lightweight fake Interaction/Channel objects and calls the
async command coroutines from `bot.main` without connecting to Discord.
"""

import argparse
import asyncio
import datetime
import sys

from typing import Any, List

# Ensure repo root is on sys.path so `import bot` works when running this script
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self._done = False

    def is_done(self):
        return self._done

    async def defer(self):
        self.deferred = True
        self._done = True
        print("[response.defer] Interaction deferred.")

    async def send_message(self, content: str, ephemeral: bool = False):
        print(f"[response.send_message] ephemeral={ephemeral} content={content}")


class FakeFollowup:
    def __init__(self):
        self.sent: List[Any] = []

    async def send(self, content: str = None, ephemeral: bool = False):
        self.sent.append({"content": content, "ephemeral": ephemeral})
        print(f"[followup.send] ephemeral={ephemeral} content={content}")


class FakeUser:
    def __init__(self, user_id: int = 1, display_name: str = "tester"):
        self.id = user_id
        self.display_name = display_name


class FakeMessage:
    def __init__(self, author_name: str, content: str, created_at=None, reactions=None):
        self.author = type("A", (), {"bot": False, "display_name": author_name})
        self.content = content
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.reactions = reactions or []


class FakeTextChannel:
    def __init__(self, messages: List[FakeMessage], guild=None):
        self._messages = messages
        self.guild = guild
        self.id = 9999
        self.name = "test-channel"
        self.mention = f"#{self.name}"

    async def history(self, limit=None, after=None, oldest_first=False):
        # Simple generator that yields messages
        print(f"[channel.history] Reading history (limit={limit}, after={after})")
        for m in self._messages:
            yield m


class FakeGuild:
    def __init__(self, guild_id: int = 12345):
        self.id = guild_id
        self.name = "Test Guild"


class FakeInteraction:
    def __init__(self, user_id: int = 1, channel=None, guild=None):
        self.user = FakeUser(user_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.channel = channel
        # Provide a guild attribute so logging code can check interaction.guild
        self.guild = guild
        # Minimal command object with a name attribute to satisfy decorators
        self.command = type("Cmd", (), {"name": "unknown"})


async def run_ask(question: str):
    import bot.main as main

    # To exercise the AI-enabled path, we return a fake key.
    # This is expected to fail at the Google client level, but proves the path is taken.
    main.get_google_api_key = lambda: "fake-api-key-for-testing"

    interaction = FakeInteraction()
    interaction.command.name = "ask"
    
    handler = main.ask_command
    if hasattr(handler, "callback"):
        handler = handler.callback

    print(f"--- Running /ask: '{question}' (AI ENABLED) ---")
    await handler(interaction, question)


async def run_summarize(hours: int):
    import bot.main as main
    
    # The summarize command does not use the AI client, so no key mocking is needed.
    main.get_google_api_key = lambda: None

    guild = FakeGuild()
    messages = [
        FakeMessage("alice", "This is a test message about project status."),
        FakeMessage("bot", "Automated note", reactions=[]),
        FakeMessage("bob", f"Another message from {hours} hours ago."),
    ]
    channel = FakeTextChannel(messages, guild=guild)
    # Set a guild on the interaction to simulate a guild channel
    interaction = FakeInteraction(channel=channel, guild=guild)
    interaction.command.name = "summarize"

    handler = main.summarize_command
    if hasattr(handler, "callback"):
        handler = handler.callback

    print(f"--- Running /summarize: last {hours} hours ---")
    await handler(interaction, hours, channel=None)


def main():
    parser = argparse.ArgumentParser(description="CLI test harness for bot commands")
    parser.add_argument("--command", required=True, choices=["ask", "summarize"]) 
    parser.add_argument("--question", help="Question text for /ask")
    parser.add_argument("--hours", type=int, default=24, help="Hours for /summarize")

    args = parser.parse_args()

    if args.command == "ask":
        if not args.question:
            print("--question is required for ask", file=sys.stderr)
            sys.exit(2)
        asyncio.run(run_ask(args.question))
    elif args.command == "summarize":
        asyncio.run(run_summarize(args.hours))


if __name__ == "__main__":
    main()
