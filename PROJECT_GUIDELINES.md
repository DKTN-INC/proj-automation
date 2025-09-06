# Project Guidelines

These guidelines describe how we collaborate, branch, commit, review, and ship changes in this repository.

## Contents
- Branching and workflow
- Commit messages
- Pull requests and reviews
- Code quality and style
- Security and secrets
- Configuration and environment
- Bot commands and UX
- Local development

---

## Branching and workflow

- Main branch: `main` is protected and must remain releasable.
- Feature branches: Use short, descriptive names, e.g.:
  - `feature/security-config`
  - `feature/ux-help-capabilities`
  - `feature/runtime-reliability`
  - `feature/ci-and-tests`
- One topic per branch. Keep diffs focused and small where possible.

Recommended flow:
1. Create a feature branch from `main`.
2. Commit and push changes early and often.
3. Open a Pull Request (PR) targeting `main`.
4. Request review and address feedback.
5. Squash-merge after approval and passing checks.

## Commit messages

- Use imperative mood and concise scope:
  - “Add Pydantic settings for security and configuration”
  - “Add help command UI”
- First line ≤ 72 chars; add context in the body if needed.
- Reference issues (e.g., “Fixes #123”) when applicable.

## Pull requests and reviews

- Include:
  - What changed and why (user impact, motivation).
  - Testing done (steps, screenshots/logs as appropriate).
  - Any follow-ups or known gaps.
- Keep PRs small and self-contained.
- Require at least one reviewer; prefer domain owners for sensitive areas (security, configuration).
- Resolve conversations or track them in follow-up tickets before merging.

## Code quality and style

- Python style:
  - Prefer type hints throughout.
  - Keep functions small; favor readability over cleverness.
- Linting/formatting:
  - Ruff + Black are recommended for lint/format.
  - Mypy for static typing.
  - Pre-commit hooks are encouraged for local consistency.
- Tests:
  - Add unit tests for new logic where feasible.
  - Keep tests fast and deterministic.

Note: If/when `.pre-commit-config.yaml` is introduced, run:
```
pre-commit install
pre-commit run --all-files
```

## Security and secrets

- Never commit secrets or tokens.
- Use environment variables for credentials.
- The settings module enforces basic validation and supports redaction in logs.

Limits and safeguards:
- Max attachment size defaults to 5 MB (configurable).
- Allowed MIME types (default): text/plain, text/markdown, application/json, image/png, image/jpeg, application/pdf.
- Use ephemeral temp directories; avoid writing outside sandbox paths.

## Configuration and environment

Environment variables recognized by the bot (from current settings):

- `DISCORD_TOKEN` (required): Discord bot token.
- `OPENAI_API_KEY` (required): OpenAI API key.
- `MAX_ATTACHMENT_BYTES` (optional, int; default 5000000): Max upload size.
- `ALLOWED_MIME_TYPES` (optional, comma-separated): Override allowed types.
- `TEMPDIR_BASE` (optional): Base path for temp sandboxes.
- `REDACT_SECRETS` (optional, “true”/“false”; default “true”): Redact secrets in logs.

Example `.env` (do not commit):
```
DISCORD_TOKEN=***
OPENAI_API_KEY=***
MAX_ATTACHMENT_BYTES=5000000
ALLOWED_MIME_TYPES=text/plain,text/markdown,application/json,image/png,image/jpeg,application/pdf
REDACT_SECRETS=true
```

## Bot commands and UX

Current application commands include:
- `/help` — Show help and common commands.
- `/capabilities` — Summarize bot capabilities.

Conventional message commands (examples that may be present or planned):
- `!lint <file>` — Run linting on a file.
- `!ocr <image>` — OCR an attached image.

Tips:
- Prefer ephemeral responses for help/diagnostics where appropriate.
- Encourage attaching relevant files with commands to reduce back-and-forth.

## Local development

- Python version: align with the project’s runtime (pin in `pyproject.toml`/`requirements.txt` when available).
- Recommended steps:
  1. Create and activate a virtualenv.
  2. Install dependencies.
  3. Set required environment variables.
  4. Run linters/tests locally before pushing.

Example:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set env vars
# run your local checks
```

---

## Ownership and contact

- Security/Configuration: changes to token handling, limits, or settings.
- UX/Commands: changes to slash commands and user-facing responses.

Document ownership is shared. Propose edits via PR to keep this up to date.