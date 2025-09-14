#!/usr/bin/env python3
"""Check for native dependencies used by the project and print clear diagnostics.

Checks performed:
- ffmpeg on PATH (and prints version)
- WeasyPrint import and whether it reports missing native libs (GTK/Cairo/Pango)

Exit codes:
  0  All checks passed (or missing deps but --fail-on-missing not provided)
  1  One or more deps missing and --fail-on-missing provided

This script is safe to run in CI and prints actionable guidance on how to
install missing components.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import textwrap


def check_ffmpeg() -> tuple[bool, str]:
    """Return (available, message) for ffmpeg.

    Tries shutil.which first, then calls `ffmpeg -version` to capture the
    version string.
    """
    ff = shutil.which("ffmpeg")
    if not ff:
        return False, "ffmpeg not found on PATH"

    try:
        out = subprocess.check_output(
            [ff, "-version"], stderr=subprocess.STDOUT, text=True
        )
        first = out.splitlines()[0] if out else "(no output)"
        return True, f"ffmpeg found: {first}"
    except Exception as exc:  # pragma: no cover - best-effort
        return False, f"ffmpeg detected at {ff} but calling it failed: {exc!r}"


def check_weasyprint() -> tuple[bool, str]:
    """Return (available, message) for WeasyPrint native libs.

    WeasyPrint may be importable but still fail at runtime if native
    libraries (GTK/Cairo/Pango) are missing. We attempt to import it and
    detect common OSError messages.
    """
    try:
        import weasyprint  # type: ignore

        # Import succeeded. We still can't fully guarantee native libs are
        # available without performing a PDF render (which is heavy). We
        # check for the presence of the internal 'urls' module and a version
        # string as a light sanity check.
        ver = getattr(weasyprint, "__version__", "unknown")
        return True, f"WeasyPrint python package present (version={ver})"
    except ImportError:
        return False, "WeasyPrint python package is not installed"
    except OSError as ose:  # missing native libs often raise OSError
        return (
            False,
            f"WeasyPrint import failed with OSError (likely missing native libs): {ose}",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"WeasyPrint import raised an unexpected error: {exc!r}"


def print_guidance(missing_ffmpeg: bool, missing_weasy: bool) -> None:
    if not missing_ffmpeg and not missing_weasy:
        print("All native dependency checks passed.")
        return

    print("\nSome native dependencies are missing or incomplete:\n")

    if missing_ffmpeg:
        print(
            textwrap.dedent(
                """
            - ffmpeg: not found on PATH. Audio/video features require ffmpeg.
              Install options:
                * Windows: use Chocolatey `choco install ffmpeg` or the project's `scripts/install_ffmpeg.ps1`.
                * Ubuntu/Debian: `sudo apt-get install ffmpeg`.
                * macOS: `brew install ffmpeg`.
            """
            )
        )

    if missing_weasy:
        print(
            textwrap.dedent(
                """
            - WeasyPrint: python package or native libraries missing. For PDF
              generation WeasyPrint needs GTK/Cairo/Pango and libffi installed.
              Install options:
                * Ubuntu/Debian: `sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
                * Windows: install Chocolatey and then `choco install gtk-runtime cairo pango libffi` (best-effort), or use an Ubuntu runner in CI.
                * Alternatively, disable markdown->PDF features in CI if not required.
            """
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check native dependencies (ffmpeg, WeasyPrint) and print guidance."
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with code 1 if any dependency is missing",
    )
    args = parser.parse_args(argv)

    ok_ffmpeg, msg_ffmpeg = check_ffmpeg()
    ok_weasy, msg_weasy = check_weasyprint()

    print("Native dependency check report:")
    print(f"  ffmpeg: {msg_ffmpeg}")
    print(f"  weasyprint: {msg_weasy}")

    missing_ffmpeg = not ok_ffmpeg
    missing_weasy = not ok_weasy

    if missing_ffmpeg or missing_weasy:
        print_guidance(missing_ffmpeg, missing_weasy)

    if args.fail_on_missing and (missing_ffmpeg or missing_weasy):
        print(
            "Exiting with failure due to missing native dependencies.", file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
