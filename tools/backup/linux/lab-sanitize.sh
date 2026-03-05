#!/usr/bin/env bash
# lab-sanitize.sh — Strip secrets from files before committing
# Usage: bash lab-sanitize.sh <file-or-directory>
set -euo pipefail

TARGET="${1:-.}"

echo "=== Sanitizing: $TARGET ==="

# Patterns to redact
PATTERNS=(
    's/sk-[a-zA-Z0-9]{20,}/sk-REDACTED/g'
    's/ghp_[a-zA-Z0-9]{36}/ghp_REDACTED/g'
    's/gho_[a-zA-Z0-9]{36}/gho_REDACTED/g'
    's/glpat-[a-zA-Z0-9\-]{20,}/glpat-REDACTED/g'
    's/Bearer [a-zA-Z0-9\.\-_]{20,}/Bearer REDACTED/g'
    's/token":\s*"[^"]+"/token": "REDACTED"/g'
    's/password":\s*"[^"]+"/password": "REDACTED"/g'
    's/apiKey":\s*"[^"]+"/apiKey": "REDACTED"/g'
    's/api_key":\s*"[^"]+"/api_key": "REDACTED"/g'
)

sanitize_file() {
    local file="$1"
    for pattern in "${PATTERNS[@]}"; do
        sed -i -E "$pattern" "$file" 2>/dev/null || true
    done
}

if [ -d "$TARGET" ]; then
    find "$TARGET" -type f \( -name '*.json' -o -name '*.yaml' -o -name '*.yml' \
        -o -name '*.ini' -o -name '*.cfg' -o -name '*.conf' -o -name '*.txt' \
        -o -name '*.md' -o -name '*.sh' -o -name '*.py' \) | while read -r f; do
        sanitize_file "$f"
    done
elif [ -f "$TARGET" ]; then
    sanitize_file "$TARGET"
else
    echo "Error: $TARGET not found"
    exit 1
fi

echo "=== Sanitization complete ==="
