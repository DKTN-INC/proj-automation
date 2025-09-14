#!/usr/bin/env python3
"""
Discord PDF Sender
Sends PDF files to Discord via webhook
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import time
import random
from typing import Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DiscordWebhookSender:
    def __init__(self, webhook_url: str):
        """Initialize Discord webhook sender.

        Args:
            webhook_url (str): Discord webhook URL
        """
        self.webhook_url = webhook_url
        self.session = requests.Session()

        # Optional runtime-configurable settings (defaults)
        self.max_retries = 3
        self.backoff_base = 1.0
        # Default max attachment size: 25 MB (Discord limit for file attachments)
        self.max_attachment_size = 25 * 1024 * 1024
        self.external_upload_url = None

        # Optional S3 config (populated from CLI or environment if used)
        self.s3_bucket: Optional[str] = None
        self.s3_region: Optional[str] = None
        self.s3_prefix: Optional[str] = None

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

        if not pdf_file.suffix.lower() == ".pdf":
            logger.error(f"File is not a PDF: {pdf_path}")
            return False

        # Check file size: default 25MB but configurable via env or argument
        file_size = pdf_file.stat().st_size
        max_size = getattr(self, "max_attachment_size", 25 * 1024 * 1024)

        if file_size > max_size:
            logger.warning(
                f"PDF file too large for webhook attachments: {file_size / (1024 * 1024):.1f}MB (max {max_size / (1024 * 1024):.1f}MB)"
            )
            # If an external upload URL is configured, try that as a fallback
            external_upload_url = getattr(self, "external_upload_url", None)
            if external_upload_url:
                link = self._upload_external_and_get_link(pdf_file, external_upload_url)
                if link:
                    return self._send_webhook_with_link(
                        pdf_file, link, message, username, avatar_url
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "Project Automation Platform"},
                "fields": [
                    {
                        "name": "📅 Generated",
                        "value": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "inline": True,
                    }
                ],
            }

            payload["embeds"] = [embed]

            # Send the file with retries/backoff for transient errors (429, 5xx, network)
            max_retries = getattr(self, "max_retries", 3)
            backoff_base = getattr(self, "backoff_base", 1.0)

            attempt = 0
            while True:
                attempt += 1
                try:
                    with open(pdf_file, "rb") as f:
                        files = {"file": (pdf_file.name, f, "application/pdf")}
                        data = {"payload_json": json.dumps(payload)}
                        response = self.session.post(
                            self.webhook_url, data=data, files=files, timeout=30
                        )

                    if response.status_code in (200, 204):
                        logger.info(f"Successfully sent {pdf_file.name} to Discord")
                        return True

                    # If payload too large or server indicates so, attempt external upload
                    if response.status_code in (413,):
                        logger.warning(
                            "Webhook rejected the attachment as too large (HTTP 413)"
                        )
                        external_upload_url = getattr(self, "external_upload_url", None)
                        if external_upload_url:
                            link = self._upload_external_and_get_link(
                                pdf_file, external_upload_url
                            )
                            if link:
                                return self._send_webhook_with_link(
                                    pdf_file, link, message, username, avatar_url
                                )
                        logger.error(
                            f"Discord webhook failed: {response.status_code} - {response.text}"
                        )
                        return False

                    # Rate limited: 429 -> retry with backoff
                    if response.status_code == 429 and attempt <= max_retries:
                        retry_after = None
                        try:
                            j = response.json()
                            retry_after = j.get("retry_after") or j.get(
                                "retry_after_ms"
                            )
                        except Exception:
                            pass

                        sleep_for = (
                            (retry_after / 1000.0)
                            if retry_after
                            else backoff_base * (2 ** (attempt - 1))
                        )
                        # add jitter
                        sleep_for = sleep_for + random.uniform(0, 0.5)
                        logger.warning(
                            f"Rate limited by Discord (429). Sleeping {sleep_for:.1f}s before retry (attempt {attempt}/{max_retries})"
                        )
                        time.sleep(sleep_for)
                        if attempt > max_retries:
                            logger.error(
                                f"Exceeded max retries ({max_retries}) for {pdf_file.name}"
                            )
                            break
                        continue

                    # 5xx server errors: retry
                    if 500 <= response.status_code < 600 and attempt <= max_retries:
                        sleep_for = backoff_base * (
                            2 ** (attempt - 1)
                        ) + random.uniform(0, 0.5)
                        logger.warning(
                            f"Server error {response.status_code}. Retrying in {sleep_for:.1f}s (attempt {attempt}/{max_retries})"
                        )
                        time.sleep(sleep_for)
                        if attempt > max_retries:
                            logger.error(
                                f"Exceeded max retries ({max_retries}) for {pdf_file.name}"
                            )
                            break
                        continue

                    # Non-retriable failure: log details and return False
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"Webhook response headers: {getattr(response, 'headers', {})}"
                        )
                        logger.debug(
                            f"Webhook response body: {getattr(response, 'text', '')}"
                        )

                    logger.error(
                        f"Discord webhook failed: {response.status_code} - {response.text}"
                    )
                    return False

                except requests.exceptions.RequestException as e:
                    if attempt <= max_retries:
                        sleep_for = backoff_base * (
                            2 ** (attempt - 1)
                        ) + random.uniform(0, 0.5)
                        logger.warning(
                            f"Network error sending to Discord: {e}. Retrying in {sleep_for:.1f}s (attempt {attempt}/{max_retries})"
                        )
                        time.sleep(sleep_for)
                        continue
                    logger.error(
                        f"Network error sending to Discord after {attempt} attempts: {e}"
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
                response = self.session.post(self.webhook_url, json=payload, timeout=30)
                # Log non-successful status codes for batch notification
                if response is not None and response.status_code != 204:
                    logger.warning(
                        f"Batch notification returned unexpected status: {response.status_code} - {getattr(response, 'text', '')}"
                    )
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

    def _upload_external_and_get_link(
        self, pdf_file: Path, upload_url: str
    ) -> Optional[str]:
        """Upload PDF to an external URL and return a public link.

        This is a minimal generic implementation that does a single POST of the
        file to `upload_url` and expects a JSON response with a `url` field.
        For production you'd implement provider-specific code (S3 presigned PUT,
        GCS, or an upload service).
        """
        try:
            with open(pdf_file, "rb") as f:
                files = {"file": (pdf_file.name, f, "application/pdf")}
                response = self.session.post(upload_url, files=files, timeout=60)
            if response.status_code in (200, 201):
                try:
                    j = response.json()
                    link = j.get("url") or j.get("file_url") or j.get("location")
                    if link:
                        logger.info(
                            f"Uploaded {pdf_file.name} to external host: {link}"
                        )
                        return link
                except Exception:
                    # Not JSON; maybe response.text contains a link
                    text = getattr(response, "text", "")
                    if text.startswith("http"):
                        logger.info(f"Uploaded and received link: {text}")
                        return text.strip()
            logger.warning(
                f"External upload failed: {response.status_code} - {getattr(response, 'text', '')}"
            )
        except Exception as e:
            logger.warning(f"External upload error: {e}")
        return None

    def _upload_to_s3_presigned(self, pdf_file: Path) -> Optional[str]:
        """Upload using S3 presigned POST/PUT. Requires boto3.

        This helper will attempt to use boto3 to create a presigned PUT URL and
        upload the file. It returns the public HTTPS URL if successful.
        """
        # Import boto3 dynamically to avoid static analysis/runtime errors when
        # the optional dependency isn't installed in the environment.
        try:
            import importlib

            boto3 = importlib.import_module("boto3")
        except Exception:
            logger.debug("boto3 not available; skipping S3 presigned upload")
            return None

        bucket = getattr(self, "s3_bucket", None)
        region = getattr(self, "s3_region", None)
        prefix = getattr(self, "s3_prefix", "") or ""
        if not bucket:
            logger.debug("S3 bucket not configured; skipping S3 upload")
            return None

        key = f"{prefix.rstrip('/')}/{pdf_file.name}" if prefix else pdf_file.name

        try:
            s3 = (
                boto3.client("s3", region_name=region) if region else boto3.client("s3")
            )
            # Generate presigned PUT URL
            presigned = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key, "ContentType": "application/pdf"},
                ExpiresIn=3600,
            )
            # Upload via PUT
            with open(pdf_file, "rb") as f:
                headers = {"Content-Type": "application/pdf"}
                resp = self.session.put(presigned, data=f, headers=headers, timeout=60)
            if resp.status_code in (200, 201):
                # Construct public URL (may depend on bucket policy)
                if region:
                    url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
                else:
                    url = f"https://{bucket}.s3.amazonaws.com/{key}"
                logger.info(f"Uploaded {pdf_file.name} to S3 at {url}")
                return url
            logger.warning(f"S3 upload returned unexpected status: {resp.status_code}")
        except Exception as e:
            # Catch any exception from boto3 or the upload and log at debug level.
            logger.warning(f"S3 presigned upload failed: {e}")
        return None

    def _send_webhook_with_link(
        self,
        pdf_file: Path,
        link: str,
        message: Optional[str],
        username: str,
        avatar_url: Optional[str],
    ) -> bool:
        """Send a webhook message linking to an externally-hosted PDF instead of attaching it."""
        payload = {
            "username": username,
            "content": message or f"📄 New idea sheet: **{pdf_file.stem}**\n{link}",
            "embeds": [
                {
                    "title": "📋 Idea Sheet Published",
                    "description": f"**File:** {pdf_file.name}\n[Download PDF]({link})",
                    "color": 0x3498DB,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "Project Automation Platform"},
                }
            ],
        }
        if avatar_url:
            payload["avatar_url"] = avatar_url

        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=30)
            if response.status_code == 204:
                logger.info(f"Successfully sent link for {pdf_file.name} to Discord")
                return True
            logger.error(
                f"Failed to send link via webhook: {response.status_code} - {getattr(response, 'text', '')}"
            )
        except Exception as e:
            logger.error(f"Network error sending link to Discord: {e}")
        return False


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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "--max-size",
        type=float,
        help="Maximum attachment size in MB (default 25)",
    )
    parser.add_argument(
        "--external-upload-url",
        help="Fallback external upload URL (POST file; expects JSON {url})",
    )
    parser.add_argument(
        "--s3-bucket",
        help="Optional S3 bucket name to use for presigned uploads as fallback",
    )
    parser.add_argument(
        "--s3-region",
        help="AWS region for S3 (optional, used to construct public URL)",
    )
    parser.add_argument(
        "--s3-prefix",
        default="",
        help="Optional key prefix to use when uploading to S3",
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

    # Configure runtime options from CLI
    if args.max_size:
        try:
            sender.max_attachment_size = int(args.max_size * 1024 * 1024)
        except Exception:
            logger.warning("Invalid --max-size value; using default")

    if args.external_upload_url:
        sender.external_upload_url = args.external_upload_url

    # S3 presigned upload config (optional)
    if args.s3_bucket:
        sender.s3_bucket = args.s3_bucket
        sender.s3_region = args.s3_region
        sender.s3_prefix = args.s3_prefix

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
