#!/usr/bin/env python3
"""
onezion-setup: Self-bootstrapping migration tool.

Run this on a NEW machine:
    python3 setup.py full-migration.zip

It will:
1. Read the migration bundle
2. Install all tools (brew, npm, pip)
3. Restore all configs
4. Install and configure agents
5. Import secrets
6. Verify everything works

Zero dependencies beyond Python 3.9+.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# ── Config ─────────────────────────────────────────────────

HOME = Path.home()
STAGING = Path("/tmp/onezion-setup")

# Agent install commands (latest stable)
AGENT_INSTALLERS = {
    "claude-code": {
        "check": "which claude",
        "install": "npm install -g @anthropic-ai/claude-code",
        "name": "Claude Code",
    },
    "hermes": {
        "check": "which hermes",
        "install": "pip install hermes-agent && hermes setup",
        "name": "Hermes Agent",
    },
    "openclaw": {
        "check": "which openclaw",
        "install": "npm install -g openclaw",
        "name": "OpenClaw",
    },
    "gemini-cli": {
        "check": "which gemini",
        "install": "npm install -g @google/gemini-cli",
        "name": "Gemini CLI",
    },
    "codex": {
        "check": "which codex",
        "install": "npm install -g @openai/codex",
        "name": "OpenAI Codex",
    },
    "docker": {
        "check": "which docker",
        "install": "brew install --cask docker",
        "name": "Docker",
    },
    "gh": {
        "check": "which gh",
        "install": "brew install gh",
        "name": "GitHub CLI",
    },
    "cloudflared": {
        "check": "which cloudflared",
        "install": "brew install cloudflared",
        "name": "Cloudflare Tunnel",
    },
}


# ── Task Runner (Mini Agent) ───────────────────────────────

@dataclass
class Task:
    name: str
    status: str = "pending"  # pending, running, done, failed, skipped
    message: str = ""


class MiniAgent:
    """A minimal task runner that bootstraps the full environment."""

    def __init__(self, bundle_path: str, dry_run: bool = False):
        self.bundle_path = Path(bundle_path)
        self.dry_run = dry_run
        self.tasks: list[Task] = []
        self.data: dict = {}

    def run(self):
        """Execute the full setup pipeline."""
        self._banner()

        # Step 1: Extract bundle
        self._step("Extract migration bundle", self._extract_bundle)

        # Step 2: Read metadata
        self._step("Read metadata", self._read_meta)

        # Step 3: Install prerequisites (brew, node, python)
        self._step("Install prerequisites", self._install_prerequisites)

        # Step 4: Restore workspace (brew, npm, pip)
        self._step("Restore workspace tools", self._restore_workspace)

        # Step 5: Install agents
        self._step("Install agents", self._install_agents)

        # Step 6: Restore agent configs
        self._step("Restore agent configs", self._restore_agent_configs)

        # Step 7: Import secrets
        self._step("Import secrets", self._import_secrets)

        # Step 8: Restore login states
        self._step("Restore login states", self._restore_cookies)

        # Step 9: Verify
        self._step("Verify installation", self._verify)

        # Summary
        self._summary()

    def _banner(self):
        print()
        print("=" * 60)
        print("  ONEZION SETUP — Self-Bootstrapping Migration")
        print("=" * 60)
        print(f"  Bundle: {self.bundle_path}")
        print(f"  Machine: {os.uname().nodename}")
        print(f"  Dry run: {self.dry_run}")
        print("=" * 60)
        print()

    def _step(self, name: str, fn):
        task = Task(name=name, status="running")
        self.tasks.append(task)
        print(f"\n{'─' * 50}")
        print(f"  [{len(self.tasks)}] {name}")
        print(f"{'─' * 50}")

        try:
            result = fn()
            if result is True:
                task.status = "done"
                print(f"  Done.")
            elif result is False:
                task.status = "failed"
                print(f"  Failed.")
            else:
                task.status = "done"
                task.message = str(result)
        except Exception as e:
            task.status = "failed"
            task.message = str(e)
            print(f"  Error: {e}")

    def _extract_bundle(self) -> bool:
        if STAGING.exists():
            shutil.rmtree(STAGING)
        STAGING.mkdir(parents=True)

        if not self.bundle_path.exists():
            print(f"  File not found: {self.bundle_path}")
            return False

        with zipfile.ZipFile(self.bundle_path, 'r') as zf:
            zf.extractall(STAGING)

        items = list(STAGING.rglob("*"))
        print(f"  Extracted {len(items)} items to {STAGING}")
        return True

    def _read_meta(self) -> bool:
        meta_file = STAGING / "meta.json"
        if meta_file.exists():
            self.data["meta"] = json.loads(meta_file.read_text())
            meta = self.data["meta"]
            print(f"  From: {meta.get('machine', 'unknown')}")
            print(f"  At: {meta.get('exported_at', 'unknown')}")
            print(f"  Layers: {meta.get('layers', {})}")
            return True
        print("  No meta.json found")
        return True

    def _install_prerequisites(self) -> bool:
        """Ensure brew, node, python are available."""
        prereqs = [
            ("Homebrew", "which brew", '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'),
            ("Node.js", "which node", "brew install node"),
            ("Python 3", "which python3", "brew install python3"),
        ]

        for name, check, install in prereqs:
            if self._run_check(check):
                print(f"  {name}: installed")
            else:
                print(f"  {name}: installing...")
                if not self.dry_run:
                    self._run_cmd(install, timeout=300)
                else:
                    print(f"    [dry-run] {install}")
        return True

    def _restore_workspace(self) -> bool:
        ws_manifest = STAGING / "workspace-manifest.json"
        if not ws_manifest.exists():
            print("  No workspace manifest found, skipping")
            return True

        data = json.loads(ws_manifest.read_text())

        # Brew
        formulae = data.get("brew_formulae", [])
        if formulae and self._run_check("which brew"):
            print(f"  Installing {len(formulae)} brew packages...")
            # Install in batches of 10
            for i in range(0, len(formulae), 10):
                batch = formulae[i:i+10]
                if not self.dry_run:
                    self._run_cmd(f"brew install {' '.join(batch)}", timeout=300)
                print(f"    {min(i+10, len(formulae))}/{len(formulae)} done")

        # npm
        npm_packages = data.get("npm_packages", [])
        if npm_packages:
            print(f"  Installing {len(npm_packages)} npm packages...")
            for pkg in npm_packages:
                if not self.dry_run:
                    self._run_cmd(f"npm install -g {pkg}", timeout=30)

        # Git config
        git_config = data.get("git_config", {})
        if git_config:
            print("  Restoring git config...")
            for key, val in git_config.items():
                if val and not self.dry_run:
                    self._run_cmd(f'git config --global {key} "{val}"')

        return True

    def _install_agents(self) -> bool:
        """Install all agents found in the migration bundle."""
        agent_dir = STAGING / "agent-sync"
        if not agent_dir.exists():
            agent_dir = STAGING

        for agent_key, info in AGENT_INSTALLERS.items():
            # Check if this agent has data in the bundle
            has_data = (agent_dir / agent_key).exists() or agent_key in str(self.data.get("meta", {}).get("layers", {}))

            if self._run_check(info["check"]):
                print(f"  {info['name']}: already installed")
            elif has_data:
                print(f"  {info['name']}: installing...")
                if not self.dry_run:
                    self._run_cmd(info["install"], timeout=120)
                else:
                    print(f"    [dry-run] {info['install']}")
            else:
                print(f"  {info['name']}: not in bundle, skipping")

        return True

    def _restore_agent_configs(self) -> bool:
        """Copy agent config files from bundle."""
        agent_dir = STAGING / "agent-sync"
        if not agent_dir.exists():
            print("  No agent configs found")
            return True

        for agent_path in sorted(agent_dir.iterdir()):
            if not agent_path.is_dir() or agent_path.name.startswith("."):
                continue

            name = agent_path.name
            print(f"  Restoring {name}...")

            if name == "hermes" and (agent_path / "backup.zip").exists():
                if not self.dry_run:
                    self._run_cmd(f"hermes import {agent_path / 'backup.zip'}", timeout=60)
                print(f"    Hermes backup imported")
            elif name == "openclaw" and (agent_path / "backup.zip").exists():
                if not self.dry_run:
                    self._run_cmd(f"openclaw backup import {agent_path / 'backup.zip'}", timeout=60)
                print(f"    OpenClaw backup imported")
            else:
                # Generic: copy config files
                dest = self._get_agent_config_dir(name)
                if dest:
                    for f in agent_path.rglob("*"):
                        if f.is_file():
                            rel = f.relative_to(agent_path)
                            target = dest / rel
                            if not self.dry_run:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(f, target)
                    print(f"    Configs copied to {dest}")
                else:
                    print(f"    Unknown agent, skipping")
        return True

    def _import_secrets(self) -> bool:
        secrets_file = STAGING / "secrets-export.json"
        if not secrets_file.exists():
            print("  No secrets file found")
            return True

        data = json.loads(secrets_file.read_text())
        secrets = data.get("secrets", [])
        print(f"  Found {len(secrets)} secrets to import")

        imported = 0
        for s in secrets:
            name = s["name"]
            value = s["value"]
            source = s["source"]

            if source == "keychain":
                if not self.dry_run:
                    service = s.get("source_path", name)
                    # Write to .env file as fallback (Keychain requires macOS)
                    env_file = HOME / ".onezion-secrets" / "imported.env"
                    env_file.parent.mkdir(parents=True, exist_ok=True)
                    with env_file.open("a") as f:
                        f.write(f'export {name}="{value}"\n')
                imported += 1
                print(f"    {name} -> ~/.onezion-secrets/imported.env")

            elif source in ("shell", "env_file"):
                if not self.dry_run:
                    env_file = HOME / ".onezion-secrets" / "imported.env"
                    env_file.parent.mkdir(parents=True, exist_ok=True)
                    with env_file.open("a") as f:
                        f.write(f'export {name}="{value}"\n')
                imported += 1

        if imported > 0:
            print(f"\n  Add to your shell profile:")
            print(f"    echo 'source ~/.onezion-secrets/imported.env' >> ~/.zshrc")

        return True

    def _restore_cookies(self) -> bool:
        cookie_zip = STAGING / "cookie-migration.zip"
        if not cookie_zip.exists():
            print("  No cookie data found")
            return True

        auth_dir = STAGING / "cookies"
        if not auth_dir.exists():
            # Extract cookie zip
            with zipfile.ZipFile(cookie_zip, 'r') as zf:
                zf.extractall(auth_dir)

        auth_src = auth_dir / "auth"
        if auth_src.exists():
            for item in auth_src.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(auth_src)
                    dest = HOME / rel
                    if not self.dry_run:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
                    print(f"    {rel}")

        return True

    def _verify(self) -> bool:
        print("  Verifying installation...")
        checks = []
        for agent_key, info in AGENT_INSTALLERS.items():
            if self._run_check(info["check"]):
                checks.append(f"  [OK] {info['name']}")
            else:
                checks.append(f"  [--] {info['name']} (not installed)")

        for c in checks:
            print(c)
        return True

    def _summary(self):
        print(f"\n{'=' * 60}")
        print("  SETUP COMPLETE")
        print(f"{'=' * 60}")

        done = sum(1 for t in self.tasks if t.status == "done")
        failed = sum(1 for t in self.tasks if t.status == "failed")

        print(f"\n  Tasks: {done} done, {failed} failed, {len(self.tasks)} total")

        if failed > 0:
            print(f"\n  Failed tasks:")
            for t in self.tasks:
                if t.status == "failed":
                    print(f"    - {t.name}: {t.message}")

        # Cleanup
        if STAGING.exists():
            shutil.rmtree(STAGING, ignore_errors=True)

        print(f"\n  Next steps:")
        print(f"    1. source ~/.onezion-secrets/imported.env")
        print(f"    2. Verify agents: hermes status, openclaw status")
        print(f"    3. Re-auth OAuth if needed (gh auth login, etc.)")
        print()

    # ── Helpers ─────────────────────────────────────────────

    def _run_check(self, cmd: str) -> bool:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _run_cmd(self, cmd: str, timeout: int = 60) -> bool:
        if self.dry_run:
            print(f"    [dry-run] {cmd}")
            return True
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0 and r.stderr:
                print(f"    Warning: {r.stderr[:100]}")
            return r.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"    Timeout: {cmd[:60]}")
            return False

    def _get_agent_config_dir(self, agent_name: str) -> Optional[Path]:
        mapping = {
            "claude-code": HOME / ".claude",
            "claude-desktop": Path.home() / "Library/Application Support/Claude",
            "gemini-cli": HOME / ".gemini",
            "codex": HOME / ".codex",
            "goose": HOME / ".config/goose",
            "opencode": HOME / ".config/opencode",
            "workbuddy": HOME / ".workbuddy",
        }
        return mapping.get(agent_name)


# ── CLI ────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="onezion-setup: Self-bootstrapping migration tool",
        epilog="Example: python3 setup.py full-migration.zip",
    )
    parser.add_argument("bundle", help="Path to full-migration.zip")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()

    agent = MiniAgent(args.bundle, dry_run=args.dry_run)
    agent.run()


if __name__ == "__main__":
    main()
