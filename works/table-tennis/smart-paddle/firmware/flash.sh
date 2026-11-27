#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load the installed ESP-IDF environment.  The host currently defaults to
# Python 3.14, while this IDF 5.5.1 installation was created with Python 3.9.
IDF_PYTHON_ENV_PATH="${IDF_PYTHON_ENV_PATH:-${HOME}/.espressif/python_env/idf5.5_py3.9_env}"
export IDF_PYTHON_ENV_PATH
. /Volumes/NormanData/sdk/esp-idf-v5.5.1/export.sh

PORT="${1:-/dev/cu.usbmodem*}"
PORT=$(ls $PORT 2>/dev/null | head -1)

if [ -z "$PORT" ]; then
    echo "No ESP32-S3 C4 board found. Plug in the board and try again."
    echo "Usage: ./flash.sh [port]"
    exit 1
fi

echo "Building firmware..."
idf.py -B build-c4 build

echo "Flashing to $PORT ..."
idf.py -B build-c4 -p "$PORT" flash

echo ""
echo "=== Flash complete ==="
echo "To monitor: idf.py -B build-c4 -p $PORT monitor"
