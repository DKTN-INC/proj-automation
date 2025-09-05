# Project Automation Repository

Project Automation is a documentation-focused repository with basic GitHub workflow automation for team collaboration and idea sheet management.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Repository Overview
- **Primary Function**: Documentation management and basic GitHub workflow triggers
- **Structure**: Minimal repository with documentation files and GitHub workflows
- **No Build Process**: This repository contains no source code to compile, no dependencies to install, and no traditional build/test processes
- **No Discord Bot**: Despite README claims, no Discord bot code exists in the repository
- **No PDF Conversion**: Despite README claims, no PDF conversion workflows are implemented

### Getting Started
- Clone the repository:
  ```bash
  git clone https://github.com/dktn7/proj-automation.git
  ```
- Navigate to repository:
  ```bash
  cd proj-automation
  ```
- **NO INSTALLATION REQUIRED**: Repository has no dependencies to install

### Available Commands
- **View repository structure**:
  ```bash
  find . -type f | grep -v ".git" | sort
  ```
  Expected output: Shows only documentation files and workflows
  
- **Test workflow functionality**:
  ```bash
  # Simulate daily standup workflow (completes in <1 second)
  echo "🚀 Starting daily standup for team: development"
  echo "📅 Date: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "👤 Triggered by: $(whoami)"
  echo "✅ Standup workflow completed successfully"
  ```

- **Test multi-channel workflow**:
  ```bash
  # Simulate multi-channel standup workflow (completes in <1 second)
  echo "🤖 Starting Discord multi-channel standup for team: development"
  echo "📺 Target channels: general,development"
  echo "📅 Date: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "👤 Triggered by: $(whoami)"
  echo "✅ Discord multi-channel standup workflow completed successfully"
  ```

### Idea Sheet Management
- **Create idea sheets**:
  ```bash
  # Create new idea sheet in the designated directory
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
  1. **Repository Navigation**: Verify you can navigate the simple directory structure
  2. **Idea Sheet Creation**: Create a test markdown file in `docs/ideasheets/` and verify it appears
  3. **Workflow Simulation**: Run the workflow echo commands and verify output format
  4. **Git Operations**: Verify git status, add, and commit operations work normally

### Important Limitations
- **NO BUILD PROCESS**: Do not attempt to build, compile, or install dependencies - none exist
- **NO TEST SUITE**: Do not look for or attempt to run unit tests - none exist  
- **NO DISCORD INTEGRATION**: Despite README claims, no Discord bot or integration code exists
- **NO PDF CONVERSION**: Despite README claims, no PDF conversion functionality exists
- **WORKFLOWS ARE ECHO ONLY**: GitHub workflows only output echo statements, no actual Discord or PDF functionality

## GitHub Workflows

### Available Workflows
1. **Daily Standup** (`.github/workflows/daily-standup.yml`)
   - Trigger: Manual via `workflow_dispatch`
   - Input: `team` (optional, default: 'development')
   - Function: Outputs formatted standup information
   - Duration: <5 seconds
   
2. **Multi-Channel Standup** (`.github/workflows/standup-multi-channel.yml`)
   - Trigger: Manual via `workflow_dispatch`  
   - Inputs: `channels` (default: 'general,development'), `team` (default: 'development')
   - Function: Outputs formatted multi-channel standup information
   - Duration: <5 seconds

### Workflow Testing
- Workflows can only be triggered via GitHub Actions interface or API
- Local testing is done by simulating the echo commands shown above
- **TIMING**: All workflows complete in under 5 seconds - no long-running operations exist

## Repository Structure Reference

### Complete File Listing
```
proj-automation/
├── .github/
│   └── workflows/
│       ├── daily-standup.yml
│       └── standup-multi-channel.yml
├── docs/
│   └── ideasheets/
│       └── README.md
├── README.md
└── WORKFLOW_ADDITION_SUMMARY.md
```

### Key Files
- `README.md`: Main documentation (contains aspirational features not implemented)
- `.github/workflows/*.yml`: GitHub Actions workflows for standup automation
- `docs/ideasheets/README.md`: Instructions for idea sheet creation
- `WORKFLOW_ADDITION_SUMMARY.md`: Documentation of workflow additions across branches

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

### Reality Check
- **DO NOT expect to find**: Source code, build scripts, package managers, test files, Discord bot code, PDF conversion tools
- **DO expect to find**: Documentation files, basic GitHub workflows, simple directory structure
- **When README mentions features not found**: The repository is in early development stage with aspirational documentation

## Troubleshooting

### Common Issues
1. **"Bot directory not found"** - This is expected, no bot code exists
2. **"No build script found"** - This is expected, no build process exists  
3. **"No PDF conversion workflow"** - This is expected, functionality not implemented
4. **"Workflow doesn't do anything"** - This is expected, workflows only output echo statements

### What Actually Works
- Creating and editing markdown files
- Git operations (add, commit, push)
- Triggering GitHub workflows (via GitHub interface)
- Basic file management and navigation

Remember: This repository is primarily for documentation and basic workflow triggers, not a traditional codebase with builds, tests, or complex functionality.