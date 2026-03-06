#!/usr/bin/env python3
"""Per-token rate limiting for the Platform API."""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT / "config" / "rate_limit_policy.json"

# In-memory sliding window counters: {token_id: [(timestamp, ...)]}
_buckets = {}


def load_policy():
    with open(POLICY_FILE) as f:
        return json.load(f)


def check_rate_limit(token_id, role):
    """Check if request is allowed. Returns (allowed, limit, remaining, reset_at)."""
    policy = load_policy()
    if not policy.get("enabled", False):
        return True, 0, 0, 0

    limits = policy.get("limits", {})
    limit = limits.get(role, 0)

    # 0 means unlimited
    if limit == 0:
        return True, 0, 0, 0

    window = policy.get("window_seconds", 60)
    now = time.time()
    cutoff = now - window

    # Get or create bucket
    key = token_id or "anonymous"
    if key not in _buckets:
        _buckets[key] = []

    # Prune old entries
    _buckets[key] = [t for t in _buckets[key] if t > cutoff]

    count = len(_buckets[key])
    remaining = max(0, limit - count)
    reset_at = cutoff + window

    if count >= limit:
        return False, limit, 0, reset_at

    # Record this request
    _buckets[key].append(now)
    return True, limit, remaining - 1, reset_at
