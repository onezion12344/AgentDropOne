<div align="center">

# AgentDropOne

### One zip. One command. Full agent workspace.

*Drop your entire AI agent environment onto any machine and watch it rebuild itself.*

---

### One-Click Install

```bash
# Fast (curl pipe):
curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash

# Safe (inspect first):
curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh -o install.sh
less install.sh     # read it first
bash install.sh
```

Detects your OS, installs prerequisites, clones AgentDropOne, and asks if you want to create or restore a bundle.

---

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![v0.5.1](https://img.shields.io/badge/version-0.5.1-purple.svg)](https://github.com/onezion12344/AgentDropOne/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Also on ClawHub](https://img.shields.io/badge/ClawHub-ready-ff69b4.svg)](https://clawhub.ai)

[![Landing Page](https://img.shields.io/badge/Landing%20Page-%20→-8A2BE2)](https://onezion12344.github.io/AgentDropOne/)

Made with love by Harry OneZion

</div>

---

## Install Flow

```bash
curl .../install.sh | bash

  Do you have a migration bundle?
    1) Yes — restore on this machine
    2) No  — export this machine
    3) Just install the tool

  Choose [1/2/3]
```

**Option 1**: Provide bundle → "Start Nanobot? [Y/n]" → 9-step restore
**Option 2**: Auto-exports everything to `Desktop/agentdropone-bundle.zip`
**Option 3**: Just installs. Run `agentdropone` anytime later.

### After install

```bash
agentdropone scan          # Discover all secrets
agentdropone export        # Create bundle from this machine
agentdropone chats         # Export chat history from 13 agents
agentdropone discover      # Scan installed agents
agentdropone sync          # Manual skill sync
agentdropone sync-on       # Install hourly auto-sync
agentdropone update        # Check & update to latest version
```

---

## What's in the bundle

```
agentdropone-bundle.zip (~224 MB)
├── workspace-manifest.json    183 brew, 31 npm, 565 pip, git, SSH, Docker
├── secrets-export.json         24 API keys (auto-discovered)
├── hermes/backup.zip           Auto-exported via CLI
├── openclaw/backup.zip         Auto-exported via CLI
├── claude-code/                Full configs + 190 skills + memory
├── chat-history/               913 sessions from 13 agents
├── cookie-migration.zip        gh, fly, superhuman, rclone, Chrome
└── meta.json
```

---

## Daily Sync

Runs automatically every hour:
```
Claude Code ←→ WorkBuddy ←→ Hermes ←→ OneDrive
```
First run: **364 skills synced, 0 conflicts**.

---

## Architecture

```
lib/nanobot/          HKUDS bootstrap mini-agent (2.2MB)
agentsync/            Secrets, orchestrator, sync, chat-export, docs
onesync-skills/       workspace-setup, cookie-manager, sync-daemon, full-migrate
install.sh             Bash one-click installer
install.ps1            Windows PowerShell installer
docs/                  GitHub Pages landing page
```

Agent-first. Not script-first. Skills work on any agent that runs Python.

---

## License

MIT — Made with love by Harry OneZion
