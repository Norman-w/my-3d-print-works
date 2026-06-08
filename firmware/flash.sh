#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load ESP-IDF environment
. /Volumes/NormanData/sdk/esp-idf-v5.5.1/export.sh

PORT="${1:-/dev/cu.usbmodem*}"
PORT=$(ls $PORT 2>/dev/null | head -1)

if [ -z "$PORT" ]; then
    echo "No ESP32-C6 found. Plug in the board and try again."
    echo "Usage: ./flash.sh [port]"
    exit 1
fi

echo "Building firmware..."
idf.py build

echo "Flashing to $PORT ..."
idf.py -p "$PORT" flash

echo ""
echo "=== Flash complete ==="
echo "To monitor: idf.py -p $PORT monitor"
