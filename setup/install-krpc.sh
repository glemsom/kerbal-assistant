#!/usr/bin/env bash
set -euo pipefail

# Install kRPC mod + Python client for Kerbal Assistant
# Usage: bash setup/install-krpc.sh

KRPC_VERSION="${KRPC_VERSION:-0.5.4}"
KSP_GAMEDATA="${KSP_GAMEDATA:-$HOME/.local/share/Steam/steamapps/common/Kerbal Space Program/GameData}"

echo "=== kRPC Installer v${KRPC_VERSION} ==="
echo "Target GameData: ${KSP_GAMEDATA}"

# 1. Download kRPC release zip
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

ZIP="${TMPDIR}/krpc-${KRPC_VERSION}.zip"
echo "Downloading krpc-${KRPC_VERSION}.zip ..."
curl -fsSL "https://github.com/krpc/krpc/releases/download/v${KRPC_VERSION}/krpc-${KRPC_VERSION}.zip" -o "$ZIP"

# 2. Extract and install mod DLL into GameData
echo "Extracting ..."
unzip -q -o "$ZIP" -d "$TMPDIR/krpc-extracted"

if [ -d "${TMPDIR}/krpc-extracted/GameData/kRPC" ]; then
    mkdir -p "${KSP_GAMEDATA}/kRPC"
    cp -r "${TMPDIR}/krpc-extracted/GameData/kRPC/"* "${KSP_GAMEDATA}/kRPC/"
    echo "kRPC mod installed → ${KSP_GAMEDATA}/kRPC/"
elif [ -d "${TMPDIR}/krpc-extracted/GameData" ]; then
    # Some releases nest differently
    cp -r "${TMPDIR}/krpc-extracted/GameData/kRPC" "${KSP_GAMEDATA}/"
    echo "kRPC mod installed → ${KSP_GAMEDATA}/kRPC/"
else
    # Fallback: find the kRPC folder
    find "${TMPDIR}/krpc-extracted" -type d -name "kRPC" -exec cp -r {} "${KSP_GAMEDATA}/" \;
    echo "kRPC mod installed (fallback) → ${KSP_GAMEDATA}/kRPC/"
fi

# 3. Install Python client
# Try pip/pip3, then pip inside a venv, then recommend
if command -v pip &>/dev/null; then
    PIP_CMD=pip
elif command -v pip3 &>/dev/null; then
    PIP_CMD=pip3
elif command -v pipx &>/dev/null; then
    echo "Installing via pipx..."
    pipx install krpc
    echo "Verifying Python import ..."
    python3 -c "import krpc; print('krpc Python client OK, version:', krpc.__version__)"
    echo ""
    echo "=== kRPC install complete ==="
    exit 0
else
    echo "pip not found. Creating venv ..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    python3 -m venv "${PROJECT_DIR}/.venv"
    "${PROJECT_DIR}/.venv/bin/pip" install krpc
    echo ""
    echo "=== kRPC install complete ==="
    echo "Python client installed in project venv (.venv/)."
    echo "Activate: source .venv/bin/activate"
    echo "Then verify: python3 -c \"import krpc; conn = krpc.connect(name='test'); print(conn.space_center.active_vessel.name)\""
    exit 0
fi

echo "Installing via $PIP_CMD ..."
$PIP_CMD install krpc 2>&1 || $PIP_CMD install --user krpc 2>&1 || $PIP_CMD install --break-system-packages krpc 2>&1

echo "Verifying Python import ..."
python3 -c "import krpc; print('krpc Python client OK, version:', krpc.__version__)" 2>&1

echo ""
echo "=== kRPC install complete ==="
echo "Launch KSP and check the kRPC toolbar icon to enable the server."
echo "Then run: python3 -c \"import krpc; conn = krpc.connect(name='test'); print(conn.space_center.active_vessel.name)\""
