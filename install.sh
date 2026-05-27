#!/usr/bin/env bash
#
# SkyNet Agent — one-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/darkwader26/SkyNet-Agent/main/install.sh | bash
#
set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
BRIGHT_RED='\033[1;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
DIM='\033[2m'
NC='\033[0m'

echo -e "${BRIGHT_RED}"
cat << "EOF"
  ███████╗██╗  ██╗██╗   ██╗███╗   ██╗███████╗████████╗
  ██╔════╝██║ ██╔╝╚██╗ ██╔╝████╗  ██║██╔════╝╚══██╔══╝
  ███████╗█████╔╝  ╚████╔╝ ██╔██╗ ██║█████╗     ██║
  ╚════██║██╔═██╗   ╚██╔╝  ██║╚██╗██║██╔══╝     ██║
  ███████║██║  ██╗   ██║   ██║ ╚████║███████╗   ██║
  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝   ╚═╝
EOF
echo -e "${NC}"

echo -e "${BRIGHT_RED}  Autonomous Agent Protocol v0.3.0${NC}"
echo -e "${DIM}  ─────────────────────────────────────────${NC}"
echo ""

# ─── Prerequisites ──────────────────────────────────────────────────────

echo -e "${CYAN}▸${NC} Checking prerequisites..."

HAS_ERROR=0

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  ✖ python3 not found. Install Python 3.10+${NC}"
    HAS_ERROR=1
else
    PYVER=$(python3 --version 2>&1)
    echo -e "${GREEN}  ✓${NC} ${DIM}${PYVER}${NC}"
fi

if ! command -v git &>/dev/null; then
    echo -e "${RED}  ✖ git not found.${NC}"
    HAS_ERROR=1
else
    echo -e "${GREEN}  ✓${NC} ${DIM}$(git --version)${NC}"
fi

if ! command -v curl &>/dev/null; then
    echo -e "${RED}  ✖ curl not found.${NC}"
    HAS_ERROR=1
else
    echo -e "${GREEN}  ✓${NC} ${DIM}$(curl --version | head -1)${NC}"
fi

if [ "$HAS_ERROR" = "1" ]; then
    echo -e "\n${RED}  Install missing prerequisites and try again.${NC}"
    exit 1
fi

echo ""

# ─── Install Location ──────────────────────────────────────────────────

INSTALL_DIR="${HOME}/SkyNet-Agent"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}  ⚠ ${INSTALL_DIR} already exists.${NC}"
    BACKUP="${INSTALL_DIR}.bak.$(date +%s)"
    echo -e "${YELLOW}  → Backing up existing to ${BACKUP}${NC}"
    mv "$INSTALL_DIR" "$BACKUP"
fi

echo -e "${CYAN}▸${NC} Cloning SkyNet Agent..."
git clone --depth=1 https://github.com/darkwader26/SkyNet-Agent.git "$INSTALL_DIR" 2>&1 | tail -1
echo -e "${GREEN}  ✓${NC} ${DIM}Cloned to ${INSTALL_DIR}${NC}"

cd "$INSTALL_DIR"
echo ""

# ─── Virtual Environment ────────────────────────────────────────────────

echo -e "${CYAN}▸${NC} Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}  ✓${NC} ${DIM}venv created${NC}"

echo -e "${CYAN}▸${NC} Installing dependencies..."
pip install -q -r requirements.txt 2>&1 | tail -3
echo -e "${GREEN}  ✓${NC} ${DIM}Dependencies installed${NC}"

echo ""

# ─── API Key Setup ─────────────────────────────────────────────────────

echo -e "${CYAN}▸${NC} Configuring API key..."
if [ -f .env ]; then
    echo -e "${YELLOW}  ⚠ .env already exists${NC}"
else
    cp .env.example .env

    echo -e "  ${DIM}Set your API key. Options:${NC}"
    echo -e "  ${DIM}  1. OPENAI_API_KEY  → https://platform.openai.com/api-keys${NC}"
    echo -e "  ${DIM}  2. OPENROUTER_API_KEY → https://openrouter.ai/keys${NC}"
    echo -e "  ${DIM}  3. DEEPSEEK_API_KEY → https://platform.deepseek.com/api_keys${NC}"
    echo ""

    read -rp "$(echo -e "${BRIGHT_RED}  Enter API key (or press Enter to skip): ${NC}")" apikey

    if [ -n "$apikey" ]; then
        # Guess provider from key prefix
        if [[ "$apikey" == sk-or-* ]]; then
            sed -i "s|OPENROUTER_API_KEY=\"\"|OPENROUTER_API_KEY=\"${apikey}\"|" .env
            echo -e "${GREEN}  ✓${NC} ${DIM}OpenRouter API key configured${NC}"
        elif [[ "$apikey" == sk-* ]]; then
            sed -i "s|OPENAI_API_KEY=\"\"|OPENAI_API_KEY=\"${apikey}\"|" .env
            echo -e "${GREEN}  ✓${NC} ${DIM}OpenAI API key configured${NC}"
        else
            sed -i "s|OPENAI_API_KEY=\"\"|OPENAI_API_KEY=\"${apikey}\"|" .env
            echo -e "${GREEN}  ✓${NC} ${DIM}API key saved (set as OPENAI_API_KEY)${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ No key set. Edit ${INSTALL_DIR}/.env later.${NC}"
    fi
fi

echo ""

# ─── Create `skynet` Command ───────────────────────────────────────────

echo -e "${CYAN}▸${NC} Creating 'skynet' command..."

WRAPPER_SCRIPT="${INSTALL_DIR}/skynet.sh"
cat > "$WRAPPER_SCRIPT" << 'WRAPPER'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
source "$DIR/venv/bin/activate"
exec python main.py "$@"
WRAPPER
chmod +x "$WRAPPER_SCRIPT"

# Symlink
SYMLINK_DIR="${HOME}/.local/bin"
mkdir -p "$SYMLINK_DIR"
ln -sf "$WRAPPER_SCRIPT" "${SYMLINK_DIR}/skynet"

# Also create skynet.sh in PATH
cp "$WRAPPER_SCRIPT" "${SYMLINK_DIR}/skynet.sh" 2>/dev/null || true

# Check if in PATH
if ! echo "$PATH" | grep -q "$SYMLINK_DIR"; then
    SHELL_CONFIG="${HOME}/.bashrc"
    if [ -n "${ZSH_VERSION:-}" ]; then
        SHELL_CONFIG="${HOME}/.zshrc"
    fi
    echo "export PATH=\"\$PATH:${SYMLINK_DIR}\"" >> "$SHELL_CONFIG"
    echo -e "${YELLOW}  ⚠ Added ${SYMLINK_DIR} to PATH in ${SHELL_CONFIG}${NC}"
    echo -e "  ${DIM}  Run: source ${SHELL_CONFIG}${NC}"
fi

echo -e "${GREEN}  ✓${NC} ${DIM}Command 'skynet' installed. Usage: skynet [options]${NC}"

echo ""

# ─── Data Directory ────────────────────────────────────────────────────

mkdir -p data

# ─── Done ──────────────────────────────────────────────────────────────

echo -e "${BRIGHT_RED}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║          INSTALLATION COMPLETE                ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "  ${DIM}To launch:${NC}"
echo -e "  ${GREEN}    skynet${NC}"
echo -e "  ${DIM}    cd ${INSTALL_DIR} && python main.py${NC}"
echo ""
echo -e "  ${DIM}Flags:${NC}"
echo -e "  ${DIM}    skynet --yolo              # Skip safety gates${NC}"
echo -e "  ${DIM}    skynet --no-improve         # Disable learning${NC}"
echo -e "  ${DIM}    skynet --no-tui             # Plain terminal mode${NC}"
echo -e "  ${DIM}    skynet -q \"search AI news\"  # Single query${NC}"
echo -e "  ${DIM}    skynet --daemon              # Background mode${NC}"
echo ""

# ─── Launch ────────────────────────────────────────────────────────────

echo -e "${CYAN}▸${NC} Launching SkyNet Agent..."
echo ""
source venv/bin/activate
exec python main.py
