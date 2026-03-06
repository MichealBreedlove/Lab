#!/usr/bin/env bash
# P43 — Sanitize: remove secrets from artifact files before commit/push
set -euo pipefail

TARGET_DIR="${1:-.}"

echo "-> Sanitizing artifacts in: $TARGET_DIR"

# Patterns to redact (case-insensitive where possible)
PATTERNS=(
    's/([Pp]assword[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/([Tt]oken[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/([Ss]ecret[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/([Cc]ookie[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/([Aa]uthorization[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/(api[_-]?[Kk]ey[\s=:"'"'"']+)[^\s<"'"'"']*/\1REDACTED/g'
    's/-----BEGIN[A-Z ]*PRIVATE KEY-----.*-----END[A-Z ]*PRIVATE KEY-----/REDACTED_PRIVATE_KEY/gs'
    's/AKIA[0-9A-Z]{16}/REDACTED_AWS_KEY/g'
    's/ghp_[a-zA-Z0-9]{36}/REDACTED_GH_TOKEN/g'
    's/sk-[a-zA-Z0-9]{48}/REDACTED_API_KEY/g'
)

COUNT=0
while IFS= read -r -d '' file; do
    # Skip binary files
    if file "$file" | grep -qE 'binary|executable|image'; then
        continue
    fi

    MODIFIED=false
    for pattern in "${PATTERNS[@]}"; do
        if grep -qPi "$(echo "$pattern" | sed 's|^s/||;s|/.*||')" "$file" 2>/dev/null; then
            perl -pi -e "$pattern" "$file" 2>/dev/null && MODIFIED=true
        fi
    done

    if [ "$MODIFIED" = true ]; then
        COUNT=$((COUNT + 1))
    fi
done < <(find "$TARGET_DIR" -type f \( -name "*.txt" -o -name "*.xml" -o -name "*.json" -o -name "*.cfg" -o -name "*.conf" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.raw" \) -print0)

# Remove .raw files (unsanitized originals)
find "$TARGET_DIR" -name "*.raw" -delete 2>/dev/null || true

echo "[OK] Sanitized $COUNT files"
