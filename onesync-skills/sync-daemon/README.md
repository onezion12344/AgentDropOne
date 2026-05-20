---
name: sync-daemon
description: >
  Lightweight config sync daemon. Watches agent config directories for changes,
  snapshots to OneDrive sync folder. Other machine picks up changes automatically.
  No WebSocket, no SSH, no exposed ports — just cloud storage sync.
version: 0.1.0
---

# sync-daemon

Lightweight config sync via cloud storage (OneDrive, Google Drive, Dropbox).

## Architecture

```
Machine A                          Machine B
  onezion-sync (watch)               onezion-sync (watch)
       |                                  |
       v                                  v
  ~/.onezion-sync/                   ~/.onezion-sync/
  (inside OneDrive sync folder)      (same folder via OneDrive)
```

## How it works

1. `onezion-sync watch` starts monitoring config directories
2. When a file changes, it copies a sanitized snapshot to `~/.onezion-sync/`
3. OneDrive syncs the folder to the other machine
4. `onezion-sync apply` on the other machine picks up changes

## What it watches

| Directory | What | Sanitize? |
|-----------|------|-----------|
| ~/.claude/ | Claude Code settings, skills | Strip secrets |
| ~/.hermes/config.yaml | Hermes config | Strip API keys |
| ~/.hermes/.env | Hermes env vars | Extract key names only |
| ~/.openclaw/openclaw.json | OpenClaw config | Strip auth tokens |
| ~/.gemini/settings.json | Gemini config | Strip OAuth tokens |
| ~/.workbuddy/mcp.json | WorkBuddy MCP config | No secrets |

## Usage

```bash
# Start watching (runs in background)
python3 sync.py watch

# One-time sync snapshot
python3 sync.py snapshot

# Apply changes from other machine
python3 sync.py apply

# Status
python3 sync.py status
```

## Security

- Secrets are NEVER synced to the cloud storage folder
- Only config structure + non-sensitive values are synced
- API keys are synced separately via onezion-agent-sync secrets
- Encrypted sync option coming later

## Adding cloud providers

This tool uses a simple sync folder approach. As long as the folder is synced
by any cloud provider (OneDrive, Google Drive, Dropbox, rclone), it works.

For rclone-based providers:
```bash
rclone sync ~/.onezion-sync remote:onezion-sync
```
