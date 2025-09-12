from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.send_pdf_to_discord import DiscordWebhookSender


def make_temp_pdf(tmp_path: Path, name="large.pdf", size=1024):
    p = tmp_path / name
    with open(p, "wb") as f:
        f.write(b"%PDF-1.4\n" + b"0" * (size - 8))
    return str(p)


def test_send_pdf_external_fallback_when_too_large(tmp_path):
    pdf_path = make_temp_pdf(tmp_path, size=1024)

    sender = DiscordWebhookSender("https://discord.com/api/webhooks/fake")
    # force file to be considered 'too large' by setting tiny max
    sender.max_attachment_size = 1
    # configure external upload endpoint
    sender.external_upload_url = "https://upload.example/api/upload"

    # stub the external upload helper to return a link and the webhook link sender to succeed
    with patch.object(
        sender,
        "_upload_external_and_get_link",
        return_value="https://example.com/file.pdf",
    ) as mock_upload, patch.object(
        sender, "_send_webhook_with_link", return_value=True
    ) as mock_send_link:
        ok = sender.send_pdf(pdf_path)

    assert ok is True
    mock_upload.assert_called()
    mock_send_link.assert_called()


def test_send_pdf_retries_on_5xx(tmp_path):
    pdf_path = make_temp_pdf(tmp_path, name="retry5xx.pdf", size=512)
    sender = DiscordWebhookSender("https://discord.com/api/webhooks/fake")
    sender.max_retries = 4
    sender.backoff_base = 0.01

    resp500 = MagicMock()
    resp500.status_code = 500

    resp204 = MagicMock()
    resp204.status_code = 204

    # session.post will return 500 twice then 204
    def post_side(*args, **kwargs):
        post_side.count += 1
        if post_side.count <= 2:
            return resp500
        return resp204

    post_side.count = 0

    with patch("time.sleep", return_value=None) as mock_sleep, patch(
        "random.uniform", return_value=0
    ), patch.object(sender.session, "post", side_effect=post_side) as mock_post:
        ok = sender.send_pdf(pdf_path)

    assert ok is True
    assert mock_post.call_count == 3
    assert mock_sleep.called
