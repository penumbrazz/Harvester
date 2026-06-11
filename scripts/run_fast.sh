#!/bin/bash
set -a && source "$(dirname "$0")/../.env" && set +a
exec "$(dirname "$0")/../.venv/bin/python" -u "$(dirname "$0")/fast_crawl.py"
