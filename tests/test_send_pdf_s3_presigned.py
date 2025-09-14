import sys
import types
from pathlib import Path

from scripts.send_pdf_to_discord import DiscordWebhookSender


class DummyResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class DummyS3Client:
    def __init__(self, *args, **kwargs):
        pass

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        # Return a dummy presigned URL; the actual upload is tested via session.put
        return "https://presigned.test/put/obj"


def test_upload_to_s3_presigned(monkeypatch, tmp_path):
    # Create a small PDF file
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n" + b"0" * 128)

    sender = DiscordWebhookSender("https://discord.test/webhook")

    # Configure S3 settings
    sender.s3_bucket = "mybucket"
    sender.s3_region = "us-west-2"
    sender.s3_prefix = "prefix"

    # Inject a fake boto3 module via sys.modules so importlib.import_module('boto3') works
    fake_boto3 = types.SimpleNamespace(client=lambda *args, **kwargs: DummyS3Client())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    # Patch the session.put to simulate successful PUT to presigned URL
    def fake_put(url, data=None, headers=None, timeout=None):
        # Ensure the presigned URL returned by boto3 is used
        assert url == "https://presigned.test/put/obj"
        return DummyResponse(status_code=200)

    monkeypatch.setattr(sender.session, "put", fake_put)

    result = sender._upload_to_s3_presigned(Path(str(pdf_path)))

    # Expect constructed public URL using bucket, region, and prefix
    assert result == "https://mybucket.s3.us-west-2.amazonaws.com/prefix/sample.pdf"

    # Clean up the fake boto3 to avoid leaking into other tests
    monkeypatch.setitem(sys.modules, "boto3", None)
