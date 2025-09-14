# Project Automation Repository

Project Automation is a multi-feature repository for team collaboration, idea sheet management, Discord bot automation, PDF conversion, and workflow integration.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Repository Overview
- **Primary Functions**: Documentation management, GitHub workflow automation, Discord bot features, PDF conversion tools, reliability and resource management utilities, automated testing
- **Structure**: The repository contains source code, scripts, documentation, workflows, and tests

### Getting Started
- Clone the repository:
  ```bash
  git clone https://github.com/dktn7/proj-automation.git
  ```
- Navigate to repository:
  ```bash
  cd proj-automation
  ```
- **Install dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
- **Environment setup**:
  - Copy `.env.template` to `.env` and fill in required values for bot and API integrations

### Available Commands
- **View repository structure**:
  ```bash
  find . -type f | grep -v ".git" | sort
  ```
  Expected output: Shows source code, documentation files, workflows, scripts, and tests

- **Run the bot**:
  ```bash
  python bot/main.py
  ```

- **Convert idea sheets to PDF**:
  ```bash
  python scripts/md_to_pdf.py docs/ideasheets/your-idea.md output.pdf/your-idea.pdf
  ```
  Or batch process:
  ```bash
  bash scripts/process_ideasheets.sh
  ```

- **Run tests**:
  ```bash
  pytest
  ```

### Idea Sheet Management
- **Create idea sheets**:
  ```bash
  echo "# Your Idea Title" > docs/ideasheets/your-idea.md
  echo "Your idea content here." >> docs/ideasheets/your-idea.md
  ```
- **View existing idea sheets**:
  ```bash
  ls -la docs/ideasheets/
  cat docs/ideasheets/README.md
  ```

## Validation

### Manual Testing Scenarios
- **ALWAYS test these scenarios after making changes**:
  1. **Repository Navigation**: Verify you can navigate the directory structure
  2. **Idea Sheet Creation**: Create a test markdown file in `docs/ideasheets/` and verify it appears
  3. **Bot Functionality**: Run `python bot/main.py` and verify bot features
  4. **PDF Conversion**: Run `python scripts/md_to_pdf.py` and verify PDF output
  5. **Workflow Simulation**: Run the workflow echo commands and verify output format
  6. **Git Operations**: Verify git status, add, and commit operations work normally
  7. **Run Tests**: Execute `pytest` and verify test results

### Important Limitations
- **Environment variables required** for bot and API integrations
- **Dependencies must be installed** from `requirements.txt`
- **README and documentation now reflect actual features**

## GitHub Workflows

### Available Workflows
1. **Daily Standup** (`.github/workflows/daily-standup.yml`)
   - Trigger: Manual via `workflow_dispatch`
   - Input: `team` (optional, default: 'development')
   - Function: Outputs formatted standup information

2. **Multi-Channel Standup** (`.github/workflows/standup-multi-channel.yml`)
   - Trigger: Manual via `workflow_dispatch`
   - Inputs: `channels` (default: 'general,development'), `team` (default: 'development')
   - Function: Outputs formatted multi-channel standup information

### Workflow Testing
- Workflows can be triggered via GitHub Actions interface or API
- Local testing is done by simulating the echo commands shown above

## Repository Structure Reference

### Complete File Listing (partial)
```
proj-automation/
├── .github/
│   └── workflows/
├── bot/
│   ├── main.py
│   ├── commands/
│   ├── features/
│   ├── *.py
├── docs/
│   └── ideasheets/
├── output.pdf/
├── scripts/
│   ├── md_to_pdf.py
│   ├── process_ideasheets.sh
│   └── *.py
├── tests/
│   └── *.py
├── utils/
│   └── *.py
├── README.md
├── requirements.txt
└── ...
```

### Key Files
- `README.md`: Main documentation
- `.github/workflows/*.yml`: GitHub Actions workflows for standup automation
- `bot/`: Discord bot code and features
- `scripts/md_to_pdf.py`: Markdown to PDF conversion script
- `scripts/process_ideasheets.sh`: Batch PDF conversion script
- `tests/`: Automated test suite
- `docs/ideasheets/README.md`: Instructions for idea sheet creation

## Common Tasks

### Documentation Updates
- Edit README.md for project description changes
- Add new idea sheets to `docs/ideasheets/`
- Modify workflow files in `.github/workflows/` for automation changes

### Git Operations
- **Standard git commands work normally**:
  ```bash
  git status
  git add .
  git commit -m "Your message"
  git push
  ```

## Troubleshooting

### Common Issues
1. **Environment variables not set** – Copy `.env.template` to `.env` and configure
2. **Dependencies not installed** – Run `pip install -r requirements.txt`
3. **PDF conversion errors** – Ensure required libraries are installed
4. **Bot errors** – Check `.env` configuration and logs
5. **Test failures** – Review test output and fix code as needed

### What Actually Works
- Creating and editing markdown files
- Git operations (add, commit, push)
- Triggering GitHub workflows (via GitHub interface)
- Running bot and PDF conversion scripts
- Automated testing

**Summary:**  
This repository includes documentation, bot code, PDF conversion, workflows, and tests. README and instructions now reflect actual implemented features.
