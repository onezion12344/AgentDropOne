"""Orchestrator: central agent discovers and calls other agents to export their data."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .registry import KNOWN_AGENTS, AgentInfo, AgentAPI


@dataclass
class AgentStatus:
    """Discovery result for one agent."""
    key: str  # registry key (e.g. "hermes")
    name: str  # display name (e.g. "Hermes Agent")
    installed: bool
    api_type: str  # "mcp", "cli", "http", "websocket", "none"
    has_export: bool  # can we call it to export?
    export_command: str  # the command to run
    manual_hint: str  # fallback instruction for user
    exported: bool = False  # whether export was successful
    export_path: str = ""  # where the export went
    error: str = ""


@dataclass
class DiscoveryReport:
    """Full discovery scan result."""
    machine: str = ""
    agents_found: list = field(default_factory=list)
    agents_with_api: list = field(default_factory=list)
    agents_manual: list = field(default_factory=list)
    secrets_count: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


# ── Discovery ──────────────────────────────────────────────

def discover_installed_agents() -> list[AgentStatus]:
    """Scan the machine for all known agents and check their status."""
    results = []

    for name, agent in KNOWN_AGENTS.items():
        status = _check_agent(agent, name)
        results.append(status)

    return results


def _check_agent(agent: AgentInfo, key: str = "") -> AgentStatus:
    """Check if an agent is installed and what API it exposes."""
    installed = False

    # Check if installed
    if agent.api.check_command:
        try:
            result = subprocess.run(
                agent.api.check_command,
                shell=True,
                capture_output=True,
                timeout=5,
            )
            installed = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    else:
        # Check if any config path exists
        home = Path.home()
        for cp in agent.config_paths:
            if (home / cp).exists():
                installed = True
                break

    has_export = bool(agent.api.export_command)

    return AgentStatus(
        key=key,
        name=agent.name,
        installed=installed,
        api_type=agent.api.type,
        has_export=has_export,
        export_command=agent.api.export_command,
        manual_hint=agent.manual_export_hint,
    )


# ── Export orchestration ───────────────────────────────────

def export_from_agent(agent_name: str, output_dir: Path) -> AgentStatus:
    """Call an agent to export its data.

    Args:
        agent_name: Registry key (e.g. "hermes") or display name (e.g. "Hermes Agent")

    Returns AgentStatus with exported=True/False and details.
    """
    # Try direct key lookup first, then search by display name
    agent = KNOWN_AGENTS.get(agent_name)
    key = agent_name
    if not agent:
        for k, a in KNOWN_AGENTS.items():
            if a.name == agent_name:
                agent = a
                key = k
                break
    if not agent:
        return AgentStatus(
            key=agent_name, name=agent_name, installed=False, api_type="none",
            has_export=False, export_command="", manual_hint="Unknown agent",
            error=f"Unknown agent: {agent_name}",
        )

    status = _check_agent(agent)
    if not status.installed:
        status.error = "Agent not installed"
        return status

    if not status.has_export:
        status.error = "No export API available — user must export manually"
        return status

    # Build export command
    export_dir = output_dir / key
    export_dir.mkdir(parents=True, exist_ok=True)
    export_file = export_dir / "backup.zip"

    cmd = agent.api.export_command.format(output=str(export_file))

    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            status.exported = True
            status.export_path = str(export_file)
        else:
            status.error = result.stderr[:200] if result.stderr else "Export command failed"
    except subprocess.TimeoutExpired:
        status.error = "Export command timed out (120s)"
    except Exception as e:
        status.error = str(e)

    return status


def export_all(output_dir: Path) -> DiscoveryReport:
    """Discover all agents and export from those with APIs.

    Returns a full report. Agents without APIs are listed for manual export.
    """
    import socket

    report = DiscoveryReport(machine=socket.gethostname())

    agents = discover_installed_agents()

    for status in agents:
        if not status.installed:
            continue

        if status.has_export:
            report.agents_with_api.append(asdict(status))
            # Try to export
            result = export_from_agent(status.key, output_dir)
            if result.exported:
                status.exported = True
                status.export_path = result.export_path
            else:
                status.error = result.error
        else:
            report.agents_manual.append(asdict(status))

        report.agents_found.append(asdict(status))

    return report


# ── Manual export guide ────────────────────────────────────

def generate_manual_guide(agents: list[AgentStatus]) -> str:
    """Generate a human-readable guide for agents that need manual export."""
    lines = [
        "# Manual Export Guide",
        "",
        "The following agents don't have automated export APIs.",
        "Please copy their configs manually to the export directory.",
        "",
    ]

    for status in agents:
        if not status.installed or status.has_export:
            continue
        agent = None
        for a in KNOWN_AGENTS.values():
            if a.name == status.name:
                agent = a
                break

        lines.append(f"## {status.name}")
        if agent:
            lines.append(f"- GitHub: https://github.com/{agent.github}")
            for cp in agent.config_paths:
                lines.append(f"- Config: ~/{cp}")
        if status.manual_hint:
            lines.append(f"- How to export: {status.manual_hint}")
        lines.append("")

    return "\n".join(lines)
