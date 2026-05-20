---
name: onezion-agent-sync
description: >
  Central agent migration orchestrator. Auto-discovers all agents on the machine,
  calls those with APIs to export their data, generates manual guides for the rest,
  and merges everything into one migration package.
version: 0.3.0
---

# onezion-agent-sync

Central agent migration orchestrator. One skill, one command, full migration.

## Core Concept

When installed on a **central agent** (Claude Code, OpenClaw, Hermes, etc.),
this skill auto-discovers ALL other agents on the machine and orchestrates export:

1. **Has API/MCP/CLI** → central agent calls it to export automatically
2. **No API** → generates a step-by-step guide telling the user what to copy
3. **Merges everything** into one migration data package

## Commands

### discover — Scan for all agents
```bash
python3 -m agentsync.cli discover
```
Shows which agents are installed, which have auto-export APIs, which need manual work.

### orchestrate — Full auto-export
```bash
python3 -m agentsync.cli orchestrate -o ~/Desktop/agent-migration
```
Runs the complete flow:
1. Exports all secrets (24+ keys from Keychain/Shell/.env/Config)
2. Calls agents with APIs (Hermes: `hermes backup`, OpenClaw: `openclaw backup create`)
3. Generates MANUAL_EXPORT_GUIDE.md for agents without APIs
4. Saves discovery-report.json with full status

### Individual commands
```bash
python3 -m agentsync.cli scan                    # Discover secrets only
python3 -m agentsync.cli export-secrets -o out.json  # Export secrets to JSON
python3 -m agentsync.cli import secrets.json      # Import on new machine
python3 -m agentsync.cli docs --all              # Discover configs from GitHub docs
```

## Orchestration Flow (for the central agent)

When user says "migrate my agent setup" or "backup everything":

```
Step 1: python3 -m agentsync.cli discover
        → Read the report: which agents have API, which need manual

Step 2: python3 -m agentsync.cli orchestrate -o ~/Desktop/agent-migration
        → Auto-exports from Hermes, OpenClaw, etc.
        → Exports all secrets
        → Generates manual guide

Step 3: For agents marked [MANUAL]:
        → Show the user the MANUAL_EXPORT_GUIDE.md
        → Guide them through each copy/paste step

Step 4: The migration package is ready at ~/Desktop/agent-migration/
        → Zip it up for transfer to new machine
```

## Registered agents and their export methods

| Agent | Install Check | Auto-Export | Command |
|-------|--------------|-------------|---------|
| Hermes Agent | `which hermes` | Yes | `hermes backup -o {output}` |
| OpenClaw | `which openclaw` | Yes | `openclaw backup create --output {output}` |
| Claude Code | `which claude` | No | Copy ~/.claude/ |
| Claude Desktop | App exists | No | Copy ~/Library/Application Support/Claude/ |
| Gemini CLI | `which gemini` | No | Copy ~/.gemini/ (re-auth OAuth) |
| OpenAI Codex | `which codex` | No | Copy ~/.codex/ (re-auth) |
| WorkBuddy | App exists | No | Use OneZion-Migrate skill |
| Goose | `which goose` | No | Copy ~/.config/goose/ |
| OpenCode | `which opencode` | No | Copy ~/.config/opencode/ |
| Casdoor | HTTP health check | No | Export from admin UI |

Add more agents in `agentsync/registry.py`.

## Adding a new agent

In `registry.py`, add to KNOWN_AGENTS:
```python
"my-agent": AgentInfo(
    name="My Agent",
    github="org/repo",
    config_paths=[".my-agent/config.json"],
    api=AgentAPI(
        type="cli",
        cli_command="my-agent",
        export_command="my-agent export --to {output}",
        check_command="which my-agent",
    ),
    manual_export_hint="Copy ~/.my-agent/ directory",
),
```

## For central agents (Claude Code, OpenClaw, Hermes)

When the user asks to migrate/backup/transfer agent setup:
1. Run `discover` first to see what's available
2. Run `orchestrate` to auto-export everything possible
3. Show the user the manual guide for remaining agents
4. Offer to zip the migration package for transfer
