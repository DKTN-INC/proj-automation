from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.send_pdf_to_discord import DiscordWebhookSender


def make_temp_pdf(tmp_path: Path, name="retry.pdf", size=512):
    p = tmp_path / name
    with open(p, "wb") as f:
        f.write(b"%PDF-1.4\n" + b"0" * (size - 8))
    return str(p)


def test_send_pdf_retries_backoff(tmp_path):
    pdf_path = make_temp_pdf(tmp_path)
    sender = DiscordWebhookSender("https://discord.com/api/webhooks/fake")

    # configure small retry budget
    sender.max_retries = 5
    sender.backoff_base = 0.01

    # Prepare fake responses: two 429s, then 204
    resp429 = MagicMock()
    resp429.status_code = 429
    resp429.json.return_value = {}

    resp204 = MagicMock()
    resp204.status_code = 204

    # side effect for session.post: 429, 429, 204
    def post_side_effect(*args, **kwargs):
        post_side_effect.count += 1
        if post_side_effect.count <= 2:
            return resp429
        return resp204

    post_side_effect.count = 0

    # Patch sleep and random.uniform to avoid delays and jitter
    with patch("time.sleep", return_value=None) as mock_sleep, patch(
        "random.uniform", return_value=0
    ), patch.object(sender.session, "post", side_effect=post_side_effect) as mock_post:
        success = sender.send_pdf(pdf_path)

    assert success is True
    # ensure we retried at least twice before success
    assert mock_post.call_count == 3
    # ensure sleep was used for backoff retries
    assert mock_sleep.called
