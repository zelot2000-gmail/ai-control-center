# Prompt: Research Report

## System
สร้าง Research Report สำหรับ R&D Agent

## Template

```markdown
# Research Report: {tool_or_technology}

**Date**: {date}
**Researcher**: {researcher}
**Status**: {adoption_status}

---

## Research Question
{research_question}

## Options Compared
1. {option_1}
2. {option_2}
3. {option_3}

## Evaluation Criteria

| Criteria              | {opt1} | {opt2} | {opt3} |
|-----------------------|--------|--------|--------|
| usefulness            | /5     | /5     | /5     |
| docker_compat         | /5     | /5     | /5     |
| wsl_compat            | /5     | /5     | /5     |
| alma8_compat          | /5     | /5     | /5     |
| security_risk         | /5     | /5     | /5     |
| maintenance_risk      | /5     | /5     | /5     |
| resource_usage        | /5     | /5     | /5     |
| token_cost            | /5     | /5     | /5     |
| rollback_plan         | /5     | /5     | /5     |
| **Total**             | **/45**| **/45**| **/45**|

## Experiment Plan
{experiment_steps}

## Results
{results}

## Pros
- {pro_1}
- {pro_2}

## Cons
- {con_1}
- {con_2}

## Risk
- {risk_1}
- {risk_2}

## Recommendation
{recommendation}

## Adoption Status
**{reject | keep watching | PoC only | staging | production-ready}**

## Next Steps
{next_steps}
```
