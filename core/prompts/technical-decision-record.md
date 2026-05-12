# Prompt: Technical Decision Record (TDR)

## System
สร้าง TDR สำหรับการตัดสินใจทางเทคนิคที่ผ่าน R&D แล้ว

## Template

```markdown
# TDR-{number}: {title}

**Date**: {date}
**Author**: {author}
**Status**: proposed | accepted | rejected | superseded
**Supersedes**: TDR-{number} (ถ้ามี)

---

## Context
{context_and_problem}

## Decision
{decision_made}

## Options Considered

### Option A: {option_a_name}
- Pros: {pros}
- Cons: {cons}

### Option B: {option_b_name}
- Pros: {pros}
- Cons: {cons}

### Option C: {option_c_name} (chosen)
- Pros: {pros}
- Cons: {cons}

## Rationale
{why_this_option}

## Consequences

### Positive
- {positive_1}

### Negative
- {negative_1}

### Risks
- {risk_1}

## Implementation Plan
1. {step_1}
2. {step_2}

## Rollback Plan
{rollback_steps}

## Review Date
{review_date}

## References
- Research Report: docs/research/experiments/{experiment_file}
- Related TDR: TDR-{number}
```
