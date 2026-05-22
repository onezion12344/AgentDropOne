#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/onezion12344/AgentDropOne.git"
INSTALL_DIR="${AGENTDROPONE_DIR:-$HOME/.agentdropone}"
BUNDLE="${1:-}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; PURPLE='\033[0;35m'; NC='\033[0m'
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

check_cmd() { command -v "$1" &>/dev/null; }

echo ""
echo -e "${PURPLE}  AgentDropOne v0.5.1${NC}"
echo ""

# ── Special flags ──────────────────────────────────────────
if [ "$BUNDLE" = "--help" ] || [ "$BUNDLE" = "-h" ]; then
    echo "Usage:"
    echo "  install.sh                         Install + choose action"
    echo "  install.sh bundle.zip              Install + restore from bundle"
    echo "  install.sh --update                Check & update to latest"
    echo ""
    exit 0
fi

if [ "$BUNDLE" = "--update" ]; then
    cd "$INSTALL_DIR" 2>/dev/null || { info "Not installed yet. Run: install.sh"; exit 1; }
    LATEST=$(curl -fsS https://api.github.com/repos/onezion12344/AgentDropOne/tags 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['name'])" 2>/dev/null || echo "?")
    CURRENT=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
    if [ "$LATEST" != "$CURRENT" ] && [ -n "$LATEST" ] && [ "$LATEST" != "?" ]; then
        info "Updating $CURRENT → $LATEST..."
        git fetch --tags --quiet 2>/dev/null; git checkout "$LATEST" --quiet 2>/dev/null
        ok "Updated to $LATEST"
    else
        ok "Up to date ($CURRENT)"
    fi
    exit 0
fi

# ── Ask: bundle first? ─────────────────────────────────────
BUNDLE_PATH=""
if [ -n "$BUNDLE" ] && [ -f "$BUNDLE" ]; then
    BUNDLE_PATH="$BUNDLE"
elif [ -n "$BUNDLE" ]; then
    err "Bundle not found: $BUNDLE"
    exit 1
else
    echo "  Do you have a migration bundle?"
    echo "    1) Yes — I have a bundle.zip (restore on this machine)"
    echo "    2) No  — Export this machine (create a new bundle)"
    echo "    3) Just install the tool (I'll use it later)"
    echo ""
    read -r -p "  Choose [1/2/3] " answer < /dev/tty
    case "$answer" in
        1) read -r -p "  Path to bundle: " path < /dev/tty; [ -f "$path" ] && BUNDLE_PATH="$path" || { err "Not found"; exit 1; } ;;
        2) ;;  # Will export after install
        3) ;;  # Just install
    esac
fi

# ── OS Detection ───────────────────────────────────────────
OS="$(uname -s)"; ARCH="$(uname -m)"
[ "$OS" = "Darwin" ] && info "Detected: macOS ($ARCH)" || info "Detected: $OS ($ARCH)"

# ── Install prerequisites ──────────────────────────────────
info "Checking prerequisites..."
{ check_cmd git || { [ "$OS" = "Darwin" ] && xcode-select --install 2>/dev/null; }; } 2>/dev/null
{ check_cmd python3 || { check_cmd brew && brew install python@3.12; }; } 2>/dev/null
check_cmd node || warn "Node.js not found (some agents need it)"
check_cmd rclone || warn "rclone not found (install for cloud sync: brew install rclone)"
check_cmd docker || warn "Docker not found (optional)"
ok "Prerequisites ready"

# ── Clone ──────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    info "AgentDropOne already at $INSTALL_DIR"
else
    info "Cloning AgentDropOne..."
    rm -rf "$INSTALL_DIR"; git clone --quiet "$REPO" "$INSTALL_DIR"
fi
ok "AgentDropOne ready at $INSTALL_DIR"

# ── Setup PATH + CLI ───────────────────────────────────────
SHELL_RC=""; case "$(basename "${SHELL:-zsh}")" in zsh) SHELL_RC="$HOME/.zshrc";; bash) SHELL_RC="$HOME/.bashrc";; esac
EXPORT_LINE="export PATH=\"\$HOME/.agentdropone:\$PATH\""
if [ -n "$SHELL_RC" ] && ! grep -qF "agentdropone" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"; echo "# AgentDropOne" >> "$SHELL_RC"; echo "$EXPORT_LINE" >> "$SHELL_RC"
    info "Added to PATH in $SHELL_RC"
fi

cat > "$INSTALL_DIR/agentdropone" << 'WRAPPER'
#!/usr/bin/env bash
ROOT="${AGENTDROPONE_DIR:-$HOME/.agentdropone}"
CMD="${1:-help}"; shift 2>/dev/null || true
case "$CMD" in
    scan)       python3 "$ROOT/onesync-skills/full-migrate/agentdropone-setup.py" "$@" --no-agent ;;
    export)     cd "$ROOT" && python3 -m agentsync.cli orchestrate -o "${1:-$HOME/Desktop/agentdropone-export}" ;;
    chats)      cd "$ROOT" && python3 -m agentsync.cli chat-export ${1:+-o "$1"} ;;
    discover)   cd "$ROOT" && python3 -m agentsync.cli discover ;;
    sync)       cd "$ROOT" && python3 -m agentsync.skill_sync ;;
    sync-on)    cd "$ROOT" && python3 -m agentsync.skill_sync --install-launchd ;;
    update)     bash "$ROOT/install.sh" --update ;;
    docs)       cd "$ROOT" && python3 -m agentsync.cli docs --all ;;
    help|-h)    echo "agentdropone {scan|export|chats|discover|sync|sync-on|update|docs}" ;;
    *)          echo "Unknown: $CMD. Try: agentdropone help" ;;
esac
WRAPPER
chmod +x "$INSTALL_DIR/agentdropone"
chmod +x "$INSTALL_DIR"/onesync-skills/full-migrate/*.py 2>/dev/null || true
export PATH="$INSTALL_DIR:$PATH"
ok "agentdropone command ready (restart terminal or: export PATH=\"\$HOME/.agentdropone:\$PATH\")"

# ── Handle bundle ──────────────────────────────────────────
if [ -n "$BUNDLE_PATH" ]; then
    # Restore from bundle
    echo ""
    info "Restoring from $BUNDLE_PATH..."

    # Ask: Nanobot?
    echo ""
    echo "  Would you like to start Nanobot as your bootstrap agent?"
    echo "  Nanobot (HKUDS, 42KB) reads the bundle and intelligently guides setup."
    echo "    y = AI-guided (auto-grabs API key from bundle)"
    echo "    n = Deterministic 9-step pipeline"
    echo ""
    read -r -p "  Start Nanobot? [Y/n] " use_ai < /dev/tty
    use_ai="${use_ai:-y}"

    if [[ "$use_ai" =~ ^[Yy] ]]; then
        cd "$INSTALL_DIR"
        python3 onesync-skills/full-migrate/agentdropone-setup.py "$BUNDLE_PATH" --agent
    else
        cd "$INSTALL_DIR"
        python3 onesync-skills/full-migrate/agentdropone-setup.py "$BUNDLE_PATH" --no-agent
    fi
elif [ "$answer" = "2" ] 2>/dev/null; then
    # Export this machine
    echo ""
    info "Creating bundle from this machine..."
    cd "$INSTALL_DIR"
    BUNDLE_OUT="$HOME/Desktop/agentdropone-bundle.zip"
    python3 -m agentsync.cli orchestrate -o /tmp/agentdropone-export
    python3 -m agentsync.cli chat-export -o /tmp/agentdropone-export/chat-history
    cd /tmp && zip -r "$BUNDLE_OUT" agentdropone-export/ >/dev/null 2>&1; rm -rf agentdropone-export
    ok "Bundle: $BUNDLE_OUT"
    echo "  Transfer to new machine, then:  install.sh $BUNDLE_OUT"
else
    # Just installed
    echo ""
    info "Ready. Try: agentdropone scan | agentdropone export | agentdropone sync-on"
fi

echo ""
ok "Done."
