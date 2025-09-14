from scripts.send_pdf_to_discord import DiscordWebhookSender


class DummyResponse:
    def __init__(self, status_code=204, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


def make_pdf_file(tmp_path, name="test.pdf", size=1024):
    path = tmp_path / name
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\n%EOF\n" + b"0" * size)
    return str(path)


def test_send_pdf_with_retry_then_success(monkeypatch, tmp_path):
    pdf_path = make_pdf_file(tmp_path)
    sent_calls = {"count": 0}

    def fake_post(url, data=None, files=None, json=None, timeout=None):
        # First call simulate 429, second call success (204)
        sent_calls["count"] += 1
        if sent_calls["count"] == 1 and files is not None:
            # Simulate rate limit
            return DummyResponse(status_code=429, json_data={"retry_after": 1000})
        # Success for attachment POST
        return DummyResponse(status_code=204)

    sender = DiscordWebhookSender("https://discord.test/webhook")
    sender.max_retries = 3
    sender.backoff_base = 0.01  # speed up test

    # Patch the session.post method
    monkeypatch.setattr(sender.session, "post", fake_post)

    assert sender.send_pdf(pdf_path) is True
    assert sent_calls["count"] >= 2


def test_send_pdf_413_then_external_fallback(monkeypatch, tmp_path):
    pdf_path = make_pdf_file(tmp_path)
    external_uploaded = {"called": False}

    from urllib.parse import urlparse

    def fake_post(url, data=None, files=None, json=None, timeout=None):
        # Parse the URL to avoid unsafe substring checks
        netloc = urlparse(url).netloc.lower()
        # If posting attachment to webhook -> simulate 413
        if files is not None and netloc == "discord.test":
            return DummyResponse(status_code=413, text="Payload Too Large")
        # If posting link message (json payload) -> success
        if json is not None and netloc == "discord.test":
            return DummyResponse(status_code=204)
        # External upload endpoint
        if netloc == "upload.test":
            # Simulate external upload returning JSON with url
            external_uploaded["called"] = True
            return DummyResponse(
                status_code=200, json_data={"url": "https://cdn.test/test.pdf"}
            )
        return DummyResponse(status_code=500)

    sender = DiscordWebhookSender("https://discord.test/webhook")
    sender.external_upload_url = "https://upload.test/upload"
    sender.max_retries = 1
    sender.backoff_base = 0.01

    monkeypatch.setattr(sender.session, "post", fake_post)

    assert sender.send_pdf(pdf_path) is True
    assert external_uploaded["called"] is True


def test_send_pdf_5xx_retries_then_fail(monkeypatch, tmp_path):
    pdf_path = make_pdf_file(tmp_path)
    calls = {"n": 0}

    def fake_post(url, data=None, files=None, json=None, timeout=None):
        calls["n"] += 1
        # Always return 500 for attachment attempts
        return DummyResponse(status_code=500, text="Server Error")

    sender = DiscordWebhookSender("https://discord.test/webhook")
    sender.max_retries = 2
    sender.backoff_base = 0.01

    monkeypatch.setattr(sender.session, "post", fake_post)

    assert sender.send_pdf(pdf_path) is False
    assert calls["n"] >= 1
