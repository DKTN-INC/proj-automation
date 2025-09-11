#!/usr/bin/env python3
"""Headless smoke-test harness for proj-automation.

Usage: python scripts/run_smoke_tests.py

This script performs local, mocked checks of core features so you can validate
that the main flows work without a real Discord token or external services.
"""
import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

from typing import Any


def check_env_vars():
    required = ["DISCORD_BOT_TOKEN"]
    optional = ["OPENAI_API_KEY", "GITHUB_TOKEN", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    print("\n[env] Checking environment variables:")
    for k in required:
        print(f"  - {k}: {'SET' if os.getenv(k) else 'MISSING'}")
    for k in optional:
        print(f"  - {k}: {'SET' if os.getenv(k) else 'missing (optional)'}")


def check_native_deps():
    print("\n[native] Checking native tools:")
    ff = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    print(f"  - ffmpeg: {'found at ' + ff if ff else 'NOT FOUND'}")
    # WeasyPrint native runtime (cairo/pango) isn't easily detectable here; rely on import warnings


def test_send_pdf_mock():
    print("\n[test] Mock send PDF via DiscordWebhookSender")
    sender_mod = None
    try:
        sender_mod = importlib.import_module("scripts.send_pdf_to_discord")
    except Exception:
        # Try loading by path fallback
        try:
            repo_root = Path(__file__).resolve().parents[1]
            mod_path = repo_root / "scripts" / "send_pdf_to_discord.py"
            if mod_path.exists():
                import importlib.util

                spec = importlib.util.spec_from_file_location("send_pdf_to_discord", str(mod_path))
                sender_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sender_mod)  # type: ignore
        except Exception as e:
            print(f"  - SKIP: send_pdf_to_discord not importable: {e}")
            return False

    DiscordWebhookSender = getattr(sender_mod, "DiscordWebhookSender", None)
    if not DiscordWebhookSender:
        print("  - SKIP: DiscordWebhookSender not found")
        return False

    # Create a tiny PDF file
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "smoke.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n" + b"0" * 128)

        sender = DiscordWebhookSender("https://discord.test/webhook")

        # Monkeypatch session.post to simulate successful attachment POST -> 204
        def fake_post(url, data=None, files=None, json=None, timeout=None):
            class R:
                status_code = 204

                def json(self):
                    return {}

            return R()

        sender.session.post = fake_post  # type: ignore
        ok = sender.send_pdf(str(pdf_path))
        print(f"  - send_pdf mocked result: {ok}")
        return ok


def test_s3_presigned_mock():
    print("\n[test] Mock S3 presigned upload path")
    sender_mod = None
    try:
        sender_mod = importlib.import_module("scripts.send_pdf_to_discord")
    except Exception:
        try:
            repo_root = Path(__file__).resolve().parents[1]
            mod_path = repo_root / "scripts" / "send_pdf_to_discord.py"
            if mod_path.exists():
                import importlib.util

                spec = importlib.util.spec_from_file_location("send_pdf_to_discord", str(mod_path))
                sender_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sender_mod)  # type: ignore
        except Exception as e:
            print(f"  - SKIP: send_pdf_to_discord not importable: {e}")
            return False

    DiscordWebhookSender = getattr(sender_mod, "DiscordWebhookSender", None)
    if not DiscordWebhookSender:
        print("  - SKIP: DiscordWebhookSender not found")
        return False

    sender = DiscordWebhookSender("https://discord.test/webhook")
    sender.s3_bucket = "smoke-bucket"
    sender.s3_region = "us-test-1"
    sender.s3_prefix = "smoke"

    # Inject fake boto3
    fake_boto3 = type("Boto3Mock", (), {"client": lambda *a, **k: type("C", (), {"generate_presigned_url": lambda *a, **k: "https://presigned.test/put"})()})()
    sys.modules["boto3"] = fake_boto3  # type: ignore

    # Patch session.put to accept presigned
    def fake_put(url, data=None, headers=None, timeout=None):
        class R:
            status_code = 200

        assert url == "https://presigned.test/put"
        return R()

    sender.session.put = fake_put  # type: ignore

    # Create small temp file
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "smoke2.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n" + b"1" * 64)
        res = sender._upload_to_s3_presigned(pdf_path)
        print(f"  - s3_presigned returned: {res}")
        return bool(res)


def test_markdown_to_html():
    print("\n[test] Markdown -> HTML (file_processor.markdown_to_html)")
    fp = None
    fp = None
    try:
        fp = importlib.import_module("utils.file_processor")
    except Exception:
        try:
            fp = importlib.import_module("file_processor")
        except Exception:
            # Try loading utils/file_processor.py directly by path
            try:
                repo_root = Path(__file__).resolve().parents[1]
                mod_path = repo_root / "utils" / "file_processor.py"
                if mod_path.exists():
                    import importlib.util

                    spec = importlib.util.spec_from_file_location("utils_file_processor", str(mod_path))
                    fp = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(fp)  # type: ignore
            except Exception as e:
                print(f"  - SKIP: file_processor not available: {e}")
                return False

    sample = "# Title\n\nThis is a test"
    try:
        # If async, run via asyncio
        func = getattr(fp, "markdown_to_html", None)
        if func is None:
            print("  - SKIP: markdown_to_html not found on file_processor")
            return False

        import inspect, asyncio

        if inspect.iscoroutinefunction(func):
            out = asyncio.get_event_loop().run_until_complete(func(sample, "Title"))
        else:
            out = func(sample, "Title")

        ok = isinstance(out, str) and len(out) > 0
        print(f"  - markdown_to_html produced HTML: {ok}")
        return ok
    except Exception as e:
        print(f"  - markdown_to_html failed: {e}")
        return False


def main():
    print("Proj-Automation smoke-test harness")
    check_env_vars()
    check_native_deps()

    results = {}
    results["send_pdf_mock"] = test_send_pdf_mock()
    results["s3_presigned_mock"] = test_s3_presigned_mock()
    results["markdown_to_html"] = test_markdown_to_html()

    print("\nSummary:")
    for k, v in results.items():
        print(f"  - {k}: {'OK' if v else 'SKIP/FAIL'}")

    # Exit code: 0 if at least the mocked send_pdf succeeded, else 2
    if results.get("send_pdf_mock"):
        print("Smoke tests completed — core send path OK")
        sys.exit(0)
    else:
        print("Smoke tests completed — core send path failed or skipped")
        sys.exit(2)


if __name__ == "__main__":
    main()
