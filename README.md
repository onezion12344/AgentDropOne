<div align="center">

# AgentDropOne

**One zip. One command. Full agent workspace.**

*Drop your entire AI agent environment onto any machine and watch it rebuild itself.*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![v0.5.1](https://img.shields.io/badge/version-0.5.1-purple.svg)](https://github.com/onezion12344/AgentDropOne/tags)
[![Also on ClawHub](https://img.shields.io/badge/ClawHub-ready-ff69b4.svg)](https://clawhub.ai)

<br>

**Made with love by Harry OneZion**

<br>

[![Landing Page](https://img.shields.io/badge/Landing%20Page-%20→-8A2BE2)](https://onezion12344.github.io/AgentDropOne/)
[![Notion Plan](https://img.shields.io/badge/Product%20Plan-%20→-lightgrey)](https://www.notion.so/Current-Product-Plan-366d45f5ce6b808990c3cd0a27c02a2e)

</div>

---

## One-Line Install

```bash
# Any Mac or Linux machine:
curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash

# With a bundle (full restore):
curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash -s -- bundle.zip

# Windows (PowerShell):
irm https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.ps1 | iex
```

No bundle? The installer **auto-detects your OS** and offers to create one from your current machine.

---

## What it does

AgentDropOne is a **self-bootstrapping migration tool** for AI agent workspaces.

```
┌────────────────────────────────────────────────────────────┐
│  One zip. Three layers. Thirteen agents. Full workspace.   │
│                                                            │
│  Layer 1: Workspace     Layer 2: Agents     Layer 3: Auth │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ brew  183    │  │ 24 API keys  │  │ GitHub CLI   │    │
│  │ npm   31     │  │ 13 agents    │  │ Fly.io       │    │
│  │ pip   565    │  │ 364 skills   │  │ Superhuman   │    │
│  │ git + SSH    │  │ MCP servers  │  │ Chrome       │    │
│  │ Docker       │  │ Memory       │  │ rclone       │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                            │
│        →  agentdropone-bundle.zip (224 MB)  →             │
└────────────────────────────────────────────────────────────┘
```

On a new machine, it asks:

```
  Would you like to start Nanobot as your bootstrap agent?
  Nanobot is a lightweight AI agent (HKUDS, 42KB) that can
  intelligently guide you through the setup process.

    y = Start Nanobot (auto-grabs API key from bundle)
    n = Deterministic mode (9 automated steps)

  Start Nanobot? [y/N]
```

**Nanobot** is embedded inside AgentDropOne (2.2MB). It reads the bundle, understands the context, and intelligently orchestrates the setup — no need for a separate agent.

---

## Daily Automated Sync

```
Claude Code (190 skills) ←→ WorkBuddy (170) ←→ Hermes (200)
        ↑                      ↑                    ↑
        └──────────────────────┴────────────────────┘
                   Hourly LaunchAgent
                         ↓
         OneDrive AgentDropOne/ bidirectional
           (push/pull to/from other machines)
```

Runs automatically every hour. First run: **364 skills synced, 0 conflicts**. Any change you make in one agent appears in all others — and syncs to OneDrive for your other machines.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `install.sh` | One-line install, auto-detects OS |
| `python3 agentdropone-setup.py bundle.zip` | Full restore on new machine |
| `python3 agentdropone-setup.py bundle.zip --agent` | Restore with Nanobot AI guide |
| `python3 -m agentsync.cli scan` | Discover all secrets (24 keys) |
| `python3 -m agentsync.cli export-secrets` | Export keys to JSON |
| `python3 -m agentsync.cli chat-export` | Export 913 sessions from 13 agents |
| `python3 -m agentsync.cli discover` | Scan installed agents |
| `python3 -m agentsync.cli orchestrate` | Auto-export from all agents |
| `python3 -m agentsync.skill_sync` | Sync skills across agents |
| `python3 -m agentsync.skill_sync --install-launchd` | Install hourly auto-sync |
| `python3 sync.py snapshot` | Config snapshot to cloud |
| `python3 sync.py watch` | Real-time config monitoring |
| `python3 sync.py push/pull` | Rclone gateway (40+ providers) |

---

## Architecture

```
AgentDropOne/
├── agentsync/                 # Core engine
│   ├── secrets.py             # 24+ API keys from 5 sources
│   ├── orchestrator.py        # Agent orchestration
│   ├── registry.py            # 12 agents with export methods
│   ├── chat_export.py         # 13-agent conversation export (913 sessions)
│   ├── skill_sync.py          # Hourly bidirectional skill sync
│   ├── docs.py                # GitHub docs crawler
│   └── cli.py                 # CLI: scan, export, import, docs, discover, orchestrate, chat-export
├── lib/nanobot/               # HKUDS bootstrap mini-agent (2.2MB, 164 files)
├── onesync-skills/            # Independent skills
│   ├── workspace-setup/       # brew/npm/pip/git/SSH/Docker
│   ├── cookie-manager/        # Browser cookies + OAuth tokens
│   ├── sync-daemon/           # Config sync via cloud storage
│   └── full-migrate/          # Bundler + setup.py + Nanobot bootstrap
├── docs/                      # GitHub Pages landing page
├── install.sh                 # Bash one-line installer
├── install.ps1                # Windows PowerShell installer
├── SKILL.md                   # Agent-readable skill file
└── pyproject.toml
```

## Supported Agents

| Agent | Auto-Export | Config Path |
|-------|------------|-------------|
| Hermes Agent | `hermes backup` | `~/.hermes/config.yaml` |
| OpenClaw | `openclaw backup create` | `~/.openclaw/openclaw.json` |
| Claude Code | Manual | `~/.claude/settings.json` |
| Claude Desktop | Manual | `~/Library/Application Support/Claude/` |
| Gemini CLI | Manual | `~/.gemini/settings.json` |
| OpenAI Codex | Manual | `~/.codex/config.toml` |
| WorkBuddy | Manual | `~/.workbuddy/mcp.json` |
| Goose | Manual | `~/.config/goose/config.yaml` |
| OpenCode | Manual | `~/.config/opencode/opencode.json` |
| CC Switch | Manual | `~/.cc-switch/settings.json` |

---

## Philosophy

> **Glue code, done right. Agent-first, not script-first.**

AgentDropOne doesn't rebuild what exists. It connects:
- **rclone** for cloud storage (40+ providers)
- **Nanobot (HKUDS)** for intelligent bootstrap
- **Hermes/OpenClaw** native backup for agent data
- **macOS Keychain** for secret storage
- **GitHub** for documentation discovery

Skills are universal — any agent that runs Python can use them.
Conflict resolution is **agent-driven**, not timestamp-based.

---

## Requirements

- Python 3.9+ (zero dependencies beyond stdlib)
- macOS / Linux / Windows (WSL)
- Cloud storage (OneDrive, Google Drive, Dropbox, or rclone)

## License

MIT — Made with love by Harry OneZion

---

<div align="center">

**[Landing Page](https://onezion12344.github.io/AgentDropOne/)** · **[Documentation](SKILL.md)** · **[Issues](https://github.com/onezion12344/AgentDropOne/issues)** · **[Tags](https://github.com/onezion12344/AgentDropOne/tags)**

*Drop one zip, get your whole world back.*

</div>
