import google.generativeai as genai


def test_generativeai_import():
    # smoke test to ensure the package import works and exposes expected symbols
    assert hasattr(genai, "GenerativeModel") or hasattr(genai, "GenerativeModel"), (
        "generativeai missing expected symbol"
    )
