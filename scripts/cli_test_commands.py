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

    async def send_message(self, content: str = None, ephemeral: bool = False, embed=None):
        if content:
            print(f"[response.send_message] ephemeral={ephemeral} content={content}")
        if embed:
            print(f"[response.send_message] ephemeral={ephemeral} embed_title='{embed.title}'")


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


async def run_idea_create(title: str):
    import bot.main as main
    interaction = FakeInteraction()
    # The idea commands are in a group, so we need to find the command differently
    handler = main.idea_group.get_command("create").callback
    print(f"--- Running /idea create: '{title}' ---")
    await handler(interaction, title)


async def run_idea_list():
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.idea_group.get_command("list").callback
    print("--- Running /idea list ---")
    await handler(interaction)


async def run_idea_view(title: str):
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.idea_group.get_command("view").callback
    print(f"--- Running /idea view: '{title}' ---")
    await handler(interaction, title)


async def run_todo_add(description: str):
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.task_group.get_command("add").callback
    print(f"--- Running /todo add: '{description}' ---")
    await handler(interaction, description)


async def run_todo_list():
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.task_group.get_command("list").callback
    print("--- Running /todo list ---")
    await handler(interaction)


async def run_todo_done(task_id: int):
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.task_group.get_command("done").callback
    print(f"--- Running /todo done: {task_id} ---")
    await handler(interaction, task_id)


async def run_todo_clear():
    import bot.main as main
    interaction = FakeInteraction()
    handler = main.task_group.get_command("clear").callback
    print("--- Running /todo clear ---")
    await handler(interaction)


def main():
    parser = argparse.ArgumentParser(description="CLI test harness for bot commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Run the ask command")
    ask_parser.add_argument("question", help="Question text for /ask")

    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Run the summarize command")
    summarize_parser.add_argument("--hours", type=int, default=24, help="Hours for /summarize")

    # Idea command
    idea_parser = subparsers.add_parser("idea", help="Run idea sheet commands")
    idea_subparsers = idea_parser.add_subparsers(dest="idea_command", required=True)
    
    idea_create_parser = idea_subparsers.add_parser("create", help="Create an idea sheet")
    idea_create_parser.add_argument("title", help="Title of the idea sheet")
    
    idea_subparsers.add_parser("list", help="List idea sheets")
    
    idea_view_parser = idea_subparsers.add_parser("view", help="View an idea sheet")
    idea_view_parser.add_argument("title", help="Title of the idea sheet to view")

    # Todo command
    todo_parser = subparsers.add_parser("todo", help="Run task tracking commands")
    todo_subparsers = todo_parser.add_subparsers(dest="todo_command", required=True)
    
    todo_add_parser = todo_subparsers.add_parser("add", help="Add a task")
    todo_add_parser.add_argument("description", help="Description of the task")
    
    todo_subparsers.add_parser("list", help="List tasks")
    
    todo_done_parser = todo_subparsers.add_parser("done", help="Mark a task as done")
    todo_done_parser.add_argument("task_id", type=int, help="ID of the task")
    
    todo_subparsers.add_parser("clear", help="Clear all tasks")

    args = parser.parse_args()

    if args.command == "ask":
        asyncio.run(run_ask(args.question))
    elif args.command == "summarize":
        asyncio.run(run_summarize(args.hours))
    elif args.command == "idea":
        if args.idea_command == "create":
            asyncio.run(run_idea_create(args.title))
        elif args.idea_command == "list":
            asyncio.run(run_idea_list())
        elif args.idea_command == "view":
            asyncio.run(run_idea_view(args.title))
    elif args.command == "todo":
        if args.todo_command == "add":
            asyncio.run(run_todo_add(args.description))
        elif args.todo_command == "list":
            asyncio.run(run_todo_list())
        elif args.todo_command == "done":
            asyncio.run(run_todo_done(args.task_id))
        elif args.todo_command == "clear":
            asyncio.run(run_todo_clear())


if __name__ == "__main__":
    main()
