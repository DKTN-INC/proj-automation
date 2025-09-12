from pathlib import Path
import types
from unittest.mock import patch, MagicMock

from scripts.send_pdf_to_discord import DiscordWebhookSender


def make_temp_pdf(tmp_path: Path, name="test.pdf", size=1024):
    p = tmp_path / name
    with open(p, "wb") as f:
        f.write(b"%PDF-1.4\n" + b"0" * (size - 8))
    return str(p)


def test_s3_presigned_upload_and_webhook_put(tmp_path):
    pdf_path = make_temp_pdf(tmp_path)

    sender = DiscordWebhookSender("https://discord.com/api/webhooks/fake")
    # Configure S3 bucket info so method tries S3
    sender.s3_bucket = "test-bucket"
    sender.s3_region = "us-east-1"
    sender.s3_prefix = "uploads"

    # Mock boto3 and its client.generate_presigned_url
    fake_presigned_url = "https://example.com/presigned-put"

    mock_s3_client = MagicMock()
    mock_s3_client.generate_presigned_url.return_value = fake_presigned_url

    # Patch importlib.import_module to return a fake boto3 module with client() -> mock_s3_client
    fake_boto3 = types.SimpleNamespace(client=lambda *args, **kwargs: mock_s3_client)

    # Patch requests.Session.put to simulate successful PUT to presigned URL
    fake_response = MagicMock()
    fake_response.status_code = 200

    with patch("importlib.import_module", return_value=fake_boto3):
        # Exercise the presigned upload helper directly
        with patch.object(
            sender.session, "put", return_value=fake_response
        ) as mock_put:
            url = sender._upload_to_s3_presigned(Path(pdf_path))

    # The helper uploads via PUT and then returns a constructed public S3 URL
    assert "test-bucket" in url
    assert "uploads/test.pdf" in url
    mock_s3_client.generate_presigned_url.assert_called()
    mock_put.assert_called()

    # Now ensure the webhook sender can post the link
    fake_webhook_response = MagicMock()
    fake_webhook_response.status_code = 204
    with patch.object(sender.session, "post", return_value=fake_webhook_response):
        sent = sender._send_webhook_with_link(
            Path(pdf_path), url, None, "PDF Bot", None
        )
    assert sent is True
