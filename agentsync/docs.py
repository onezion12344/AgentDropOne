"""GitHub docs crawler: discover agent config structures from repos."""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .registry import AgentInfo, KNOWN_AGENTS


@dataclass
class ConfigPattern:
    """A discovered config file pattern."""
    path: str  # e.g. "~/.config/agent/settings.json"
    format: str  # json, yaml, toml, env, ini
    description: str  # what it contains
    source: str  # "readme", "docs", "code", "inferred"


@dataclass
class AgentDocProfile:
    """Discovered documentation profile for an agent."""
    name: str
    github: str
    readme_excerpt: str = ""
    config_patterns: list = field(default_factory=list)
    env_vars: list = field(default_factory=list)
    install_commands: list = field(default_factory=list)
    discovered_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


# ── GitHub raw content fetcher ─────────────────────────────

GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_API = "https://api.github.com"


def _fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch URL content as string."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "onezion-agent-sync/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def fetch_readme(github_repo: str, branch: str = "main") -> Optional[str]:
    """Fetch README from a GitHub repo."""
    for filename in ["README.md", "README.rst", "README"]:
        url = f"{GITHUB_RAW}/{github_repo}/{branch}/{filename}"
        content = _fetch_url(url)
        if content:
            return content
    # Try master branch
    for filename in ["README.md", "README"]:
        url = f"{GITHUB_RAW}/{github_repo}/master/{filename}"
        content = _fetch_url(url)
        if content:
            return content
    return None


def fetch_repo_tree(github_repo: str, branch: str = "main") -> Optional[list[dict]]:
    """Fetch repository file tree (top-level only)."""
    url = f"{GITHUB_API}/repos/{github_repo}/git/trees/{branch}"
    data = _fetch_url(url)
    if data:
        try:
            result = json.loads(data)
            return result.get("tree", [])
        except json.JSONDecodeError:
            pass
    return None


# ── Config pattern discovery ───────────────────────────────

# Patterns to look for in READMEs
_CONFIG_PATH_PATTERNS = [
    # ~/.config/agent-name/settings.json
    re.compile(r'[~$HOME]+[/\.]+(?:config|\.config)?/?([a-zA-Z0-9_-]+)/(?:(?:config|settings)\.(json|yaml|yml|toml))', re.IGNORECASE),
    # ~/.agent-name/config.json
    re.compile(r'[~$HOME]+[/\.]+([a-zA-Z0-9_-]+)/(?:config|settings)\.(json|yaml|yml|toml)', re.IGNORECASE),
    # /path/to/.env
    re.compile(r'[~$HOME]+[/\.]+([a-zA-Z0-9_-]+/?)\.(env)', re.IGNORECASE),
]

_ENV_VAR_PATTERNS = [
    re.compile(r'(?:export\s+)?([A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET|_API))\s*=', re.MULTILINE),
    re.compile(r'`([A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET|_API))`'),
]

_INSTALL_PATTERNS = [
    re.compile(r'(?:npm|brew|pip|cargo)\s+(?:install|i)\s+([^\s]+)', re.IGNORECASE),
]


def discover_from_readme(readme: str, agent_name: str) -> AgentDocProfile:
    """Parse a README to discover config patterns."""
    profile = AgentDocProfile(
        name=agent_name,
        github="",
        readme_excerpt=readme[:500] if readme else "",
    )

    if not readme:
        return profile

    # Find config paths
    seen_paths = set()
    for pattern in _CONFIG_PATH_PATTERNS:
        for match in pattern.finditer(readme):
            path_str = match.group(0).strip()
            if path_str not in seen_paths:
                seen_paths.add(path_str)
                # Determine format from extension
                ext = match.group(2) if match.lastindex >= 2 else "json"
                profile.config_patterns.append(asdict(ConfigPattern(
                    path=path_str,
                    format=ext,
                    description="",
                    source="readme",
                )))

    # Find env vars
    seen_vars = set()
    for pattern in _ENV_VAR_PATTERNS:
        for match in pattern.finditer(readme):
            var = match.group(1)
            if var not in seen_vars and len(var) > 3:
                seen_vars.add(var)
                profile.env_vars.append(var)

    # Find install commands
    for pattern in _INSTALL_PATTERNS:
        for match in pattern.finditer(readme):
            cmd = match.group(0).strip()
            if cmd not in profile.install_commands:
                profile.install_commands.append(cmd)

    return profile


def discover_from_tree(tree: list[dict], agent_name: str) -> list[str]:
    """Parse repo file tree to find config-related files."""
    config_files = []
    config_keywords = {"config", "settings", "env", "rc", "preferences", "conf"}
    config_extensions = {".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".conf"}

    for item in tree:
        name = item.get("name", "").lower()
        # Check if it looks like a config file
        if any(kw in name for kw in config_keywords) or any(name.endswith(ext) for ext in config_extensions):
            config_files.append(item.get("name", ""))

    return config_files


# ── Main discovery function ────────────────────────────────

def discover_agent(agent_name: str, cache_dir: Optional[Path] = None) -> AgentDocProfile:
    """Discover an agent's config structure from its GitHub repo.

    Args:
        agent_name: Name of the agent (must be in KNOWN_AGENTS)
        cache_dir: Optional directory to cache discovered profiles

    Returns:
        AgentDocProfile with discovered config patterns
    """
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"{agent_name}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return AgentDocProfile(**data)
            except (json.JSONDecodeError, TypeError):
                pass

    agent = KNOWN_AGENTS.get(agent_name)
    if not agent:
        return AgentDocProfile(name=agent_name, github="unknown")

    # Fetch README
    readme = fetch_readme(agent.github)

    # Discover from README
    profile = discover_from_readme(readme or "", agent_name)
    profile.github = agent.github

    # Also fetch repo tree for additional discovery
    tree = fetch_repo_tree(agent.github)
    if tree:
        config_files = discover_from_tree(tree, agent_name)
        # Add any config files from tree that aren't already in patterns
        existing_paths = {p["path"] for p in profile.config_patterns}
        for cf in config_files:
            if cf not in existing_paths:
                profile.config_patterns.append(asdict(ConfigPattern(
                    path=cf,
                    format=cf.rsplit(".", 1)[-1] if "." in cf else "unknown",
                    description="found in repo root",
                    source="tree",
                )))

    # Merge with known registry data
    if agent.config_paths:
        existing_paths = {p["path"] for p in profile.config_patterns}
        for cp in agent.config_paths:
            if cp not in existing_paths:
                profile.config_patterns.append(asdict(ConfigPattern(
                    path=cp,
                    format=agent.config_format,
                    description="from registry",
                    source="registry",
                )))

    # Cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{agent_name}.json").write_text(profile.to_json())

    return profile


def discover_all_agents(cache_dir: Optional[Path] = None) -> dict[str, AgentDocProfile]:
    """Discover config structures for all known agents."""
    profiles = {}
    for name in KNOWN_AGENTS:
        profiles[name] = discover_agent(name, cache_dir)
    return profiles
