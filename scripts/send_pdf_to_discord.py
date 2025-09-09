#!/usr/bin/env python3
"""
Discord PDF Sender
Sends PDF files to Discord via webhook
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import requests


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DiscordWebhookSender:
    def __init__(self, webhook_url):
        """
        Initialize Discord webhook sender.

        Args:
            webhook_url (str): Discord webhook URL
        """
        self.webhook_url = webhook_url
        self.session = requests.Session()

    def send_pdf(self, pdf_path, message=None, username="PDF Bot", avatar_url=None):
        """
        Send a PDF file to Discord via webhook.

        Args:
            pdf_path (str): Path to the PDF file
            message (str): Optional message to send with the PDF
            username (str): Bot username for the message
            avatar_url (str): Avatar URL for the bot

        Returns:
            bool: True if successful, False otherwise
        """
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return False

        if pdf_file.suffix.lower() != ".pdf":
            logger.error(f"File is not a PDF: {pdf_path}")
            return False

        # Check file size (Discord limit is 25MB for webhooks)
        file_size = pdf_file.stat().st_size
        max_size = 25 * 1024 * 1024  # 25MB in bytes

        if file_size > max_size:
            logger.error(
                f"PDF file too large: {file_size / (1024 * 1024):.1f}MB (max 25MB)"
            )
            return False

        try:
            # Prepare the payload
            payload = {
                "username": username,
                "content": message or f"📄 New idea sheet: **{pdf_file.stem}**",
            }

            if avatar_url:
                payload["avatar_url"] = avatar_url

            # Create embed with file info
            embed = {
                "title": "📋 Idea Sheet Published",
                "description": f"**File:** {pdf_file.name}\n**Size:** {file_size / 1024:.1f} KB",
                "color": 0x3498DB,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Project Automation Platform"},
                "fields": [
                    {
                        "name": "📅 Generated",
                        "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "inline": True,
                    }
                ],
            }

            payload["embeds"] = [embed]

            # Send the file
            with pdf_file.open("rb") as f:
                files = {"file": (pdf_file.name, f, "application/pdf")}

                data = {"payload_json": json.dumps(payload)}

                response = self.session.post(
                    self.webhook_url, data=data, files=files, timeout=30
                )

            if response.status_code == 204:
                logger.info(f"Successfully sent {pdf_file.name} to Discord")
                return True
            else:
                logger.error(
                    f"Discord webhook failed: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending to Discord: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending PDF to Discord: {e}")
            return False

    def send_multiple_pdfs(self, pdf_paths, batch_message=None):
        """
        Send multiple PDF files to Discord.

        Args:
            pdf_paths (list): List of PDF file paths
            batch_message (str): Optional message for the batch

        Returns:
            dict: Results with success/failure counts and details
        """
        results = {"total": len(pdf_paths), "successful": 0, "failed": 0, "details": []}

        if batch_message:
            # Send batch notification first
            payload = {
                "username": "PDF Bot",
                "content": batch_message,
                "embeds": [
                    {
                        "title": "📚 Batch PDF Upload",
                        "description": f"Processing {len(pdf_paths)} PDF files...",
                        "color": 0x2ECC71,
                    }
                ],
            }

            try:
                self.session.post(self.webhook_url, json=payload, timeout=30)
            except Exception as e:
                logger.warning(f"Failed to send batch notification: {e}")

        # Send each PDF
        for pdf_path in pdf_paths:
            try:
                success = self.send_pdf(pdf_path)
                if success:
                    results["successful"] += 1
                    results["details"].append({"file": pdf_path, "status": "success"})
                else:
                    results["failed"] += 1
                    results["details"].append({"file": pdf_path, "status": "failed"})
            except Exception as e:
                logger.error(f"Error processing {pdf_path}: {e}")
                results["failed"] += 1
                results["details"].append(
                    {"file": pdf_path, "status": "error", "error": str(e)}
                )

        logger.info(
            f"Batch complete: {results['successful']} successful, {results['failed']} failed"
        )
        return results


def send_notification(webhook_url, title, message, color=0x3498DB):
    """
    Send a simple notification message to Discord.

    Args:
        webhook_url (str): Discord webhook URL
        title (str): Message title
        message (str): Message content
        color (int): Embed color

    Returns:
        bool: True if successful, False otherwise
    """
    payload = {
        "username": "Automation Bot",
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        return response.status_code == 204
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Send PDF files to Discord via webhook"
    )
    parser.add_argument("input", nargs="+", help="PDF file(s) or directory to send")
    parser.add_argument("--webhook", required=True, help="Discord webhook URL")
    parser.add_argument("--message", help="Custom message to send with PDF(s)")
    parser.add_argument(
        "--username", default="PDF Bot", help="Bot username (default: PDF Bot)"
    )
    parser.add_argument("--avatar", help="Avatar URL for the bot")
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="File pattern for directory mode (default: *.pdf)",
    )
    parser.add_argument(
        "--notify-only", action="store_true", help="Send notification only, no files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate webhook URL
    if not args.webhook.startswith("https://discord.com/api/webhooks/"):
        logger.error("Invalid Discord webhook URL")
        sys.exit(1)

    if args.notify_only:
        # Send notification only
        title = "🔄 PDF Processing Complete"
        message = (
            args.message or "PDF generation and processing completed successfully."
        )
        success = send_notification(args.webhook, title, message)
        if success:
            print("Notification sent successfully")
        else:
            print("Failed to send notification")
            sys.exit(1)
        return

    # Initialize sender
    sender = DiscordWebhookSender(args.webhook)

    # Collect PDF files
    pdf_files = []

    for input_path in args.input:
        path = Path(input_path)

        if path.is_file() and path.suffix.lower() == ".pdf":
            pdf_files.append(str(path))
        elif path.is_dir():
            # Find all PDF files in directory
            found_pdfs = list(path.glob(args.pattern))
            pdf_files.extend([str(p) for p in found_pdfs if p.suffix.lower() == ".pdf"])
        else:
            logger.warning(f"Skipping invalid path: {input_path}")

    if not pdf_files:
        logger.error("No PDF files found to send")
        sys.exit(1)

    # Send PDFs
    if len(pdf_files) == 1:
        # Send single PDF
        success = sender.send_pdf(
            pdf_files[0], args.message, args.username, args.avatar
        )
        if success:
            print(f"Successfully sent {Path(pdf_files[0]).name}")
        else:
            print(f"Failed to send {Path(pdf_files[0]).name}")
            sys.exit(1)
    else:
        # Send multiple PDFs
        batch_message = (
            args.message or f"📚 Publishing {len(pdf_files)} new idea sheets"
        )
        results = sender.send_multiple_pdfs(pdf_files, batch_message)

        print(f"Batch results: {results['successful']}/{results['total']} successful")

        if args.verbose:
            for detail in results["details"]:
                status_emoji = "✅" if detail["status"] == "success" else "❌"
                print(f"  {status_emoji} {Path(detail['file']).name}")

        if results["failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
