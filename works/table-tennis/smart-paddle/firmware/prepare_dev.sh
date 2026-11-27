#!/bin/bash
# 兼容旧入口：转发到 firmware/dev.sh
exec "$(cd "$(dirname "$0")" && pwd)/dev.sh"
