"""Agent registry: known agents with their APIs, MCP interfaces, and export methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentAPI:
    """How to interact with this agent programmatically."""
    type: str  # "mcp", "cli", "http", "websocket", "none"
    endpoint: str = ""  # e.g. "http://localhost:18789/v1/chat/completions"
    cli_command: str = ""  # e.g. "hermes", "openclaw"
    export_command: str = ""  # e.g. "hermes backup", "openclaw backup create"
    mcp_name: str = ""  # MCP server name if available
    check_command: str = ""  # command to check if agent is installed


@dataclass
class AgentInfo:
    name: str
    github: str  # "owner/repo"
    config_paths: list[str] = field(default_factory=list)
    config_format: str = "json"
    env_files: list[str] = field(default_factory=list)
    keychain_services: list[str] = field(default_factory=list)
    docs_url: str = ""
    notes: str = ""
    api: AgentAPI = field(default_factory=lambda: AgentAPI(type="none"))
    manual_export_hint: str = ""  # what to tell user if no API


# ── Known agents ───────────────────────────────────────────

KNOWN_AGENTS: dict[str, AgentInfo] = {
    "hermes": AgentInfo(
        name="Hermes Agent",
        github="NousResearch/hermes-agent",
        config_paths=[".hermes/config.yaml"],
        config_format="yaml",
        env_files=[".hermes/.env"],
        api=AgentAPI(
            type="cli",
            cli_command="hermes",
            export_command="hermes backup -o {output}",
            check_command="which hermes",
        ),
    ),
    "openclaw": AgentInfo(
        name="OpenClaw",
        github="openclaw/openclaw",
        config_paths=[".openclaw/openclaw.json"],
        config_format="json",
        api=AgentAPI(
            type="cli",
            cli_command="openclaw",
            export_command="openclaw backup create --output {output}",
            check_command="which openclaw",
        ),
    ),
    "claude-code": AgentInfo(
        name="Claude Code",
        github="anthropics/claude-code",
        config_paths=[".claude/settings.json", ".claude/settings.local.json"],
        config_format="json",
        api=AgentAPI(
            type="mcp",
            mcp_name="claude-code",
            check_command="which claude",
        ),
        manual_export_hint="Copy ~/.claude/ directory to the new machine",
    ),
    "claude-desktop": AgentInfo(
        name="Claude Desktop",
        github="anthropics/claude-desktop",
        config_paths=["Library/Application Support/Claude/config.json"],
        config_format="json",
        api=AgentAPI(type="none"),
        manual_export_hint="Copy ~/Library/Application Support/Claude/ directory",
    ),
    "gemini-cli": AgentInfo(
        name="Gemini CLI",
        github="google-gemini/gemini-cli",
        config_paths=[".gemini/settings.json", ".gemini/config/config.json"],
        config_format="json",
        api=AgentAPI(
            type="cli",
            cli_command="gemini",
            check_command="which gemini",
        ),
        manual_export_hint="Copy ~/.gemini/ directory. OAuth token in .gemini/oauth_creds.json needs re-auth on new machine.",
    ),
    "codex": AgentInfo(
        name="OpenAI Codex",
        github="openai/codex",
        config_paths=[".codex/config.toml"],
        config_format="toml",
        api=AgentAPI(
            type="cli",
            cli_command="codex",
            check_command="which codex",
        ),
        manual_export_hint="Copy ~/.codex/ directory. Auth tokens in .codex/auth.json may need re-login.",
    ),
    "workbuddy": AgentInfo(
        name="WorkBuddy",
        github="anthropics/workbuddy",
        config_paths=[".workbuddy/mcp.json"],
        config_format="json",
        api=AgentAPI(
            type="cli",
            cli_command="workbuddy",
            check_command="ls ~/Library/Application\\ Support/WorkBuddy/",
        ),
        manual_export_hint="Use OneZion-Migrate skill: bash ~/.workbuddy/skills/OneZion-Migrate/scripts/export_agent.sh --secrets",
    ),
    "goose": AgentInfo(
        name="Goose",
        github="block/goose",
        config_paths=[".config/goose/config.yaml"],
        config_format="yaml",
        api=AgentAPI(
            type="cli",
            cli_command="goose",
            check_command="which goose",
        ),
        manual_export_hint="Copy ~/.config/goose/ directory",
    ),
    "opencode": AgentInfo(
        name="OpenCode",
        github="opencode-ai/opencode",
        config_paths=[".config/opencode/opencode.json"],
        config_format="json",
        api=AgentAPI(
            type="cli",
            cli_command="opencode",
            check_command="which opencode",
        ),
        manual_export_hint="Copy ~/.config/opencode/ directory",
    ),
    "casdoor": AgentInfo(
        name="Casdoor",
        github="casdoor/casdoor",
        config_format="yaml",
        api=AgentAPI(
            type="http",
            endpoint="http://localhost:8000/api",
            check_command="curl -s http://localhost:8000/api/health",
        ),
        manual_export_hint="Export Casdoor config from admin UI: http://localhost:8000",
    ),
    "cc-switch": AgentInfo(
        name="CC Switch",
        github="farion1231/cc-switch",
        config_paths=[".cc-switch/settings.json"],
        config_format="json",
        api=AgentAPI(
            type="cli",
            cli_command="cc-switch",
            check_command="test -d ~/.cc-switch",
        ),
        manual_export_hint="Copy ~/.cc-switch/ directory (settings.json + cc-switch.db + skills/)",
    ),
}


def get_agent(name: str) -> Optional[AgentInfo]:
    return KNOWN_AGENTS.get(name)


def list_agents() -> list[AgentInfo]:
    return list(KNOWN_AGENTS.values())


def list_agents_with_api() -> list[AgentInfo]:
    """List agents that have a programmatic API."""
    return [a for a in KNOWN_AGENTS.values() if a.api.type != "none"]


def list_agents_without_api() -> list[AgentInfo]:
    """List agents that require manual export."""
    return [a for a in KNOWN_AGENTS.values() if a.api.type == "none"]
