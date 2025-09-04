# Project Automation (Discord bot + CI)

A professional automation platform integrating Discord and GitHub for modern teams. Streamline collaboration, documentation, and publishing workflows with powerful bots and CI tools.

---

## Overview

Project Automation provides:
- **Discord bot** for real-time team collaboration, Q&A, and summarization.
- **Forum utilities** for posting Idea Sheets with tags directly from Markdown.
- **CI/CD pipeline** for converting Markdown docs to PDFs and publishing them to Discord forums.

Perfect for technical teams, open source communities, and anyone looking to automate knowledge sharing between chat and code.

---

## Features

### Discord Bot
- **Mention Chat:** Easily mention teammates and reference GitHub issues or PRs.
- **Slash Commands:** `/ask` for quick questions, `/summarize` to get readable summaries.
- **Automated Notifications:** Get updates on CI status, new Idea Sheets, and more.

### Forum Utilities
- **Idea Sheets:** Write your ideas in Markdown, add tags, and let the system post them automatically.
- **Tagging & Categorization:** Organize community contributions for easy discovery.

### CI/CD Pipeline
- **Markdown to PDF:** Every push to the idea sheets directory triggers a workflow converting `.md` files to PDFs.
- **Discord Publishing:** PDFs are automatically posted to a designated Discord forum channel.
- **Automated Documentation:** Keep your team’s knowledge base up to date with zero manual effort.

---

## Setup

1. **Clone the repo**
   ```sh
   git clone https://github.com/dktn7/proj-automation.git
   ```
2. **Configure Discord Bot**
   - Set up a Discord bot and add its token in `.env`.
   - Adjust permissions and add it to your server.
3. **Configure GitHub Actions**
   - GitHub Actions are pre-configured for CI/CD.
   - Set secrets for Discord Webhook and other integrations in your repo settings.

4. **Directory Structure**
   ```
   proj-automation/
   ├── docs/
   │   └── ideasheets/    # Markdown files for ideas
   ├── bot/               # Discord bot source
   ├── .github/workflows/ # CI/CD definitions
   └── README.md
   ```

---

## Usage

- **Collaborate:** Use Discord bot commands to ask questions, mention users, and summarize discussions.
- **Contribute Ideas:** Create a Markdown file in `docs/ideasheets/` and push – CI will handle the rest.
- **Stay Updated:** Watch Discord forums for new PDFs and summaries.

---

## Contributing

We welcome contributions! Please open an issue or pull request:
1. Fork the repository
2. Make your changes
3. Submit a PR with a clear description

---

## License

MIT License

---

## Contact

For questions or support, open a GitHub issue or contact the maintainer via Discord.