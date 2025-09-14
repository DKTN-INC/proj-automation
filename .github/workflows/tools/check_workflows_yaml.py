#!/usr/bin/env python3
"""
Simple YAML syntax checker for GitHub Actions workflows.
Attempts to install PyYAML if missing (falls back to printing instructions).
"""

from pathlib import Path
import subprocess
import sys


try:
    import yaml
except Exception:
    print("PyYAML not found; attempting to install via pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML"])
        import yaml
    except Exception as e:
        print("Failed to install PyYAML automatically:", e)
        print(
            "Please install it manually (python -m pip install PyYAML) and re-run this script."
        )
        sys.exit(2)

had_error = False
workflows_dir = Path(".github") / "workflows"
files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
if not files:
    print("No workflow YAML files found under .github/workflows/")
    sys.exit(0)

for path in files:
    print(f"Checking {path}...")
    try:
        with Path(path).open(encoding="utf-8") as f:
            text = f.read()
        # Parse all documents to catch multi-doc cases
        list(yaml.safe_load_all(text))
    except Exception as e:
        had_error = True
        print(f"ERROR parsing {path}:\n{e}\n")

if had_error:
    print("YAML syntax check failed for one or more workflow files.")
    sys.exit(1)
else:
    print("All workflow YAML files parsed successfully.")
    sys.exit(0)
