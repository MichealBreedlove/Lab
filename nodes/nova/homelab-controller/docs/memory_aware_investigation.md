# Memory-Aware Investigation

## Overview

When a new incident arrives, the investigator consults cluster memory before generating conclusions. This enriches investigations with historical context, improving accuracy and reducing time-to-resolution.

## Enrichment Flow

1. New incident triggers investigation
2. `build_investigation_context()` searches memory for similar past incidents
3. Prior successful remediations are ranked by success rate
4. Confidence is adjusted based on historical patterns
5. Investigation output includes memory-enriched fields

## Enriched Fields

| Field | Type | Description |
|-------|------|-------------|
| `related_cases` | list[str] | Memory IDs of similar past incidents |
| `historical_success_rate` | float | Success rate of prior remediations for similar issues |
| `prior_recommended_actions` | list[dict] | Ranked actions with success rates |
| `memory_informed_confidence` | float | Confidence adjusted by historical data |

## Confidence Adjustment

- Base confidence: 0.70
- History shows >80% success rate: +0.15 (capped at 0.95)
- History shows >50% success rate: +0.05
- History shows <30% success rate with 3+ data points: -0.15 (floor at 0.30)
- 3+ related cases found: +0.05

When sufficient history exists (≥3 remediations), the final confidence blends:
`blended = investigation_confidence * 0.6 + memory_confidence * 0.4`

## Recording to Memory

Every investigation is automatically recorded to memory with category `investigation`. Every remediation outcome should be recorded with category `remediation`. This creates the growing knowledge base that future investigations draw from.

## Cold Start Behavior

When no history exists for an incident type:
- `historical_success_rate` = None
- `prior_recommended_actions` = []
- `memory_informed_confidence` uses base confidence (0.70)
- Investigation proceeds normally with playbook-only evidence

## Safety

- Memory enrichment is **non-blocking** — if the memory system fails, investigation continues without it
- Memory cannot override playbook evidence or policy engine decisions
- Memory cannot lower approval requirements
