"""Secret discovery: find all API keys and tokens across the system."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Secret:
    name: str
    value: str
    source: str  # "keychain", "shell", "env_file", "config_file", "agent_config"
    source_path: str
    agent: Optional[str] = None


@dataclass
class SecretManifest:
    version: str = "1.0"
    machine: str = ""
    exported_at: str = ""
    secrets: list = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


HOME = Path.home()


def discover_all() -> list[Secret]:
    """Run all discovery methods and return deduplicated secrets."""
    found: dict[str, Secret] = {}

    def _add(secrets: list[Secret]):
        for s in secrets:
            if s.name not in found:
                found[s.name] = s

    _add(_discover_keychain())
    _add(_discover_shell_profiles())
    _add(_discover_env_files())
    _add(_discover_config_files())
    _add(_discover_agent_configs())

    return list(found.values())


# ── Keychain ───────────────────────────────────────────────

# (keychain_service, keychain_account, display_name)
KEYCHAIN_ENTRIES = [
    ("WorkBuddy-Maton", "MATON_API_KEY", "MATON_API_KEY"),
    ("notion-api-key", "notion", "NOTION_TOKEN"),
    ("workbuddy", "AIGOHOTEL_API_KEY", "AIGOHOTEL_API_KEY"),
    ("workbuddy", "ASSEMBLYAI_API_KEY", "ASSEMBLYAI_API_KEY"),
    ("workbuddy", "CHATLAB_TOKEN", "CHATLAB_TOKEN"),
    ("workbuddy", "DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
    ("workbuddy", "OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
    ("workbuddy", "RIZE_API_KEY", "RIZE_API_KEY"),
]


def _discover_keychain() -> list[Secret]:
    secrets = []
    for service, account, name in KEYCHAIN_ENTRIES:
        value = _keychain_get(service, account)
        if value:
            secrets.append(Secret(
                name=name, value=value,
                source="keychain", source_path=service,
            ))
    return secrets


def _keychain_get(service: str, account: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ── Shell profiles ─────────────────────────────────────────

_SHELL_PROFILES = [
    HOME / ".zshrc",
    HOME / ".bashrc",
    HOME / ".bash_profile",
]

# Match: export KEY="value" or KEY=value
# Names must contain _KEY, _TOKEN, _SECRET, _PASS, _CREDENTIAL, or _AUTH
_ENV_RE = re.compile(
    r'^(?:export\s+)?([A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET|_PASS(?:WORD)?|_CREDENTIAL|_AUTH(?:_TOKEN)?))'
    r'\s*=\s*["\']?([^"\'\s$(][^"\'\n]*?)["\']?\s*$',
    re.MULTILINE,
)


def _discover_shell_profiles() -> list[Secret]:
    secrets = []
    for path in _SHELL_PROFILES:
        if path.exists():
            secrets.extend(_parse_kv_file(path, "shell"))
    return secrets


def _is_valid_value(value: str) -> bool:
    if not value or value in ('""', "''"):
        return False
    if value.startswith(("$( ", "$(", "${")):
        return False
    if re.match(r'^[A-Z][A-Z0-9_]*=', value):
        return False
    return True


def _parse_kv_file(path: Path, source: str) -> list[Secret]:
    """Parse KEY=VALUE pairs from a file."""
    text = path.read_text(errors="ignore")
    secrets = []
    for m in _ENV_RE.finditer(text):
        name, value = m.group(1), m.group(2)
        if _is_valid_value(value):
            secrets.append(Secret(
                name=name, value=value,
                source=source, source_path=str(path),
            ))
    return secrets


# ── .env files ─────────────────────────────────────────────

# Known locations
_KNOWN_ENV_FILES = [
    HOME / ".hermes" / ".env",
    HOME / ".openchronicle" / ".env",
    HOME / ".workbuddy" / "mimo-mcp" / ".env",
    HOME / ".workbuddy" / "open-video-overview" / ".env",
    HOME / "ai-goofish-monitor" / ".env",
    HOME / "Developer" / "video-use" / ".env",
    HOME / "WorkBuddy" / "credentials" / "sapling.env",
]

# Directories to auto-scan for .env files
_ENV_SCAN_DIRS = [
    HOME / ".workbuddy" / "skills",
    HOME / "Developer",
    HOME / "Projects",
]


def _discover_env_files() -> list[Secret]:
    paths = list(_KNOWN_ENV_FILES)

    # Auto-discover .env in scan directories
    for scan_dir in _ENV_SCAN_DIRS:
        if scan_dir.exists():
            for env_path in scan_dir.rglob(".env"):
                if env_path not in paths and _should_scan(env_path):
                    paths.append(env_path)

    secrets = []
    for path in paths:
        if path.exists():
            secrets.extend(_parse_kv_file(path, "env_file"))
    return secrets


def _should_scan(path: Path) -> bool:
    """Skip heavy directories."""
    skip = {"node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build"}
    return not any(part in skip for part in path.parts)


# ── Config files (structured) ─────────────────────────────

def _discover_config_files() -> list[Secret]:
    secrets = []

    # Fly.io
    fly_path = HOME / ".fly" / "config.yml"
    if fly_path.exists():
        secrets.extend(_parse_fly_config(fly_path))

    # rclone
    rclone_path = HOME / ".config" / "rclone" / "rclone.conf"
    if rclone_path.exists():
        secrets.extend(_parse_ini_file(rclone_path, "config_file"))

    # GitHub CLI
    gh_path = HOME / ".config" / "gh" / "hosts.yml"
    if gh_path.exists():
        secrets.extend(_parse_yaml_values(gh_path, "config_file", ["oauth_token"]))

    # Superhuman CLI
    sh_path = HOME / ".config" / "superhuman-cli" / "tokens.json"
    if sh_path.exists():
        secrets.extend(_parse_json_tokens(sh_path, "config_file"))

    return secrets


def _parse_fly_config(path: Path) -> list[Secret]:
    """Parse Fly.io config.yml for tokens."""
    secrets = []
    text = path.read_text(errors="ignore")
    for match in re.finditer(r'^\s*(access_token|metrics_token):\s*(\S+)', text, re.MULTILINE):
        secrets.append(Secret(
            name=f"FLY_{match.group(1).upper()}", value=match.group(2),
            source="config_file", source_path=str(path),
        ))
    return secrets


def _parse_ini_file(path: Path, source: str) -> list[Secret]:
    """Parse INI-style config (like rclone.conf) for secret values."""
    secrets = []
    text = path.read_text(errors="ignore")
    secret_keys = {"secret_access_key", "secret_key", "pass", "password", "token", "api_key"}
    current_section = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
        elif "=" in line:
            key, _, value = line.partition("=")
            key = key.strip().lower()
            value = value.strip()
            if key in secret_keys and value:
                name = f"{current_section}_{key}".upper() if current_section else key.upper()
                secrets.append(Secret(
                    name=name, value=value,
                    source=source, source_path=str(path),
                ))
    return secrets


def _parse_yaml_values(path: Path, source: str, target_keys: list[str]) -> list[Secret]:
    """Extract specific keys from a simple YAML file."""
    secrets = []
    text = path.read_text(errors="ignore")
    for key in target_keys:
        match = re.search(rf'^\s*{key}:\s*(\S+)', text, re.MULTILINE)
        if match:
            secrets.append(Secret(
                name=f"GITHUB_{key.upper()}", value=match.group(1),
                source=source, source_path=str(path),
            ))
    return secrets


def _parse_json_tokens(path: Path, source: str) -> list[Secret]:
    """Extract token-like values from a JSON file."""
    secrets = []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return secrets

    token_keys = {"access_token", "refresh_token", "id_token", "token", "api_key", "secret"}
    _walk_json(data, [], secrets, token_keys, source, str(path))
    return secrets


def _walk_json(obj, path_parts: list, secrets: list, target_keys: set, source: str, source_path: str):
    """Recursively walk JSON looking for token keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = path_parts + [k]
            if k in target_keys and isinstance(v, str) and v and len(v) > 10:
                name = "_".join(p.upper() for p in current_path[-2:]) if len(current_path) > 1 else k.upper()
                secrets.append(Secret(
                    name=name, value=v,
                    source=source, source_path=source_path,
                ))
            else:
                _walk_json(v, current_path, secrets, target_keys, source, source_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_json(item, path_parts + [str(i)], secrets, target_keys, source, source_path)


# ── Agent config files ─────────────────────────────────────

_AGENT_CONFIGS = [
    {
        "agent": "claude-code",
        "path": HOME / ".claude" / "settings.json",
        "keys": [
            ("env.ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN"),
            ("env.ANTHROPIC_BASE_URL", "ANTHROPIC_BASE_URL"),
        ],
    },
]


def _discover_agent_configs() -> list[Secret]:
    secrets = []
    for cfg in _AGENT_CONFIGS:
        path = cfg["path"]
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for json_path, key_name in cfg["keys"]:
            value = _get_nested(data, json_path)
            if value and isinstance(value, str) and not value.startswith("adapter-dummy"):
                secrets.append(Secret(
                    name=key_name, value=value,
                    source="agent_config", source_path=str(path),
                    agent=cfg["agent"],
                ))
    return secrets


def _get_nested(data: dict, dotted_path: str):
    parts = dotted_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


# ── Export / Import ────────────────────────────────────────

def export_manifest(secrets: list[Secret], output_path: Optional[Path] = None) -> Path:
    import socket
    from datetime import datetime, timezone

    manifest = SecretManifest(
        machine=socket.gethostname(),
        exported_at=datetime.now(timezone.utc).isoformat(),
        secrets=[asdict(s) for s in secrets],
    )
    if output_path is None:
        output_path = Path.cwd() / "secrets-export.json"
    output_path.write_text(manifest.to_json())
    return output_path


def import_manifest(manifest_path: Path, dry_run: bool = False) -> list[str]:
    """Import secrets from a manifest file. Returns list of actions taken."""
    data = json.loads(manifest_path.read_text())
    actions = []

    for s in data.get("secrets", []):
        name = s["name"]
        value = s["value"]
        source = s["source"]
        source_path = s["source_path"]

        if source == "keychain":
            if dry_run:
                actions.append(f"[dry-run] Would write {name} to keychain ({source_path})")
            else:
                _keychain_set(source_path, name, value)
                actions.append(f"Wrote {name} to keychain ({source_path})")

        elif source in ("shell", "env_file"):
            if dry_run:
                actions.append(f"[dry-run] Would set {name} in {source_path}")
            else:
                _write_env_var(source_path, name, value)
                actions.append(f"Set {name} in {source_path}")

        elif source == "config_file":
            if dry_run:
                actions.append(f"[dry-run] Would restore {name} to {source_path}")
            else:
                actions.append(f"Skipped {name} in {source_path} (config file, manual restore)")

        elif source == "agent_config":
            if dry_run:
                actions.append(f"[dry-run] Would set {name} in {source_path}")
            else:
                actions.append(f"Skipped {name} in {source_path} (agent config, manual restore)")

    return actions


def _keychain_set(service: str, account: str, value: str):
    """Write a secret to macOS Keychain."""
    # Delete existing entry first (ignore error if not found)
    subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", account],
        capture_output=True, timeout=5,
    )
    # Add new entry
    subprocess.run(
        ["security", "add-generic-password", "-s", service, "-a", account, "-w", value],
        capture_output=True, timeout=5,
    )


def _write_env_var(file_path: str, name: str, value: str):
    """Append or update a KEY=VALUE in a file."""
    path = Path(file_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        text = path.read_text()
        pattern = re.compile(rf'^(?:export\s+)?{re.escape(name)}=.*$', re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f'export {name}="{value}"', text)
            path.write_text(text)
            return
    # Append
    with path.open("a") as f:
        f.write(f'\nexport {name}="{value}"\n')
