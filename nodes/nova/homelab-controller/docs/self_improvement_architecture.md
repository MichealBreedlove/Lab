# Self-Improvement Architecture

## Overview

The self-improvement loop allows the platform to learn from incidents and gradually improve its own documentation, playbooks, and templates — safely and with human oversight.

## Workflow

```
Incident Closed
      |
      v
After-Action Review (P59)
  - What playbook was used?
  - What was recommended vs what happened?
  - Did a human override the AI?
  - What lessons were learned?
      |
      v
Improvement Proposal (P60)
  - Convert lessons into typed proposals
  - Types: doc_update, template_update, playbook_update,
           threshold_update, alert_mapping, policy_change
  - Assign risk level (low/medium/high)
      |
      v
Validation (P61)
  - Schema check: is the proposal well-formed?
  - Simulation check: would it cause harm?
  - Test suite check: would tests still pass?
      |
      v
Promotion Decision (P62)
  - auto_promote: documentation & template updates
  - require_review: playbook & threshold changes
  - deny: policy changes (always require human)
      |
      v
Safe Auto-Promotion (P63)
  - Only documentation_update and artifact_template_update
  - All others require explicit human approval
  - Audit trail for every promotion
```

## Safety Properties

1. **No uncontrolled changes**: Policy engine gates all promotions
2. **Human-in-the-loop**: Non-trivial changes always require review
3. **Audit trail**: Every review, proposal, validation, and promotion is logged
4. **Event bus integration**: All lifecycle events emitted for observability
5. **Rollback**: Proposals can be rejected at any stage

## Data Model

```
data/self_improvement/
  reviews/        AAR-*.json     (after-action reviews)
  proposals/      PROP-*.json    (improvement proposals)
  validations/    VAL-*.json     (validation results)
  promoted/       PROM-*.json    (promoted artifacts)
```

## Event Types

- `self_improvement.review.created`
- `self_improvement.proposal.created`
- `self_improvement.validation.completed`
- `self_improvement.promotion.applied`
