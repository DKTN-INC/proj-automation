# Constraint files removed — rationale and guidance

This project previously included a `constraints.txt` file and a small
installer helper that used that constraints file. The constraints approach
was removed from the repository to reduce developer confusion and avoid
resolver conflicts that can occur when pinning platform-specific wheel
versions (for example, OpenCV and native dependencies).

Why it was removed
- Constraint files can help reduce pip solver backtracking, but they also
  increase maintenance burden and may cause `ResolutionImpossible` in
  mixed environments (CI vs developer machines) when native wheels differ.
- The constraints file in this repo contained several platform-specific
  pins which caused more problems than benefits during iterative development
  and on CI runners with differing OS/toolchains.

What changed
- The repository no longer contains `constraints.txt` or the
  `scripts/install_with_constraints.ps1` helper.
- Install dependencies using the standard mechanisms described in
  `README.md` (virtualenv + `pip install -r requirements.txt`) or with
  modern tools that manage pins reproducibly (for example `pip-tools`,
  `poetry lock`, or `pip freeze` inside a reproducible environment).

If you need pinned installs for a specific environment
- For CI, prefer an explicit lockfile generated from the CI environment
  (for example: create a virtualenv on the runner and run `pip freeze`),
  or use a tool like `pip-tools` to generate an environment-specific
  `requirements.txt` from `requirements.in`.
- If you need a constraints file for a narrowly-scoped environment, keep
  it out of the global repo root and store it in an environment-specific
  directory (for example `ci/constraints/ubuntu-20.04.txt`) and reference
  it explicitly from CI workflow configuration.

Former notable pins (for reference)
```text
markdown==3.5.0
Jinja2==3.1.0
weasyprint==59.0
pdfkit==1.0.0
pymdown-extensions==10.0.0
discord.py==2.3.0
python-dotenv==1.0.0
google-generativeai==0.1.0
Pillow==10.0.0
pytesseract==0.3.10
pydub==0.25.1
aiosqlite==0.19.0
PyGithub==1.59.0
beautifulsoup4==4.12.0
aiohttp==3.8.0
python-magic==0.4.27
python-dateutil==2.8.0
aiofiles==23.0.0
requests==2.31.0
colorama==0.4.6
psutil==5.9.0
boto3==1.28.0
```

If you want help regenerating an environment-specific constraints file
or adding a CI-managed lockfile, I can prepare a small workflow or
`pip-tools` recipe — tell me which target environment you want supported.
