# Browser Performance Benchmark

**Date**: YYYY-MM-DD
**Researcher**: [agent / person]
**Tool**: Chrome DevTools MCP / Lighthouse
**Environment**: local / dev / staging

---

## Summary

| Metric            | Value | Rating (Good/OK/Poor) |
|-------------------|-------|-----------------------|
| Page Load Time    |       |                       |
| First Paint       |       |                       |
| DOM Content Load  |       |                       |
| Total Requests    |       |                       |
| Total Transfer    |       |                       |
| JS Bundle Size    |       |                       |
| CSS Size          |       |                       |

---

## Pages Tested

| URL                           | Load Time | Notes |
|-------------------------------|-----------|-------|
| http://127.0.0.1:3000         |           |       |
| http://127.0.0.1:3000/command |           |       |
| http://127.0.0.1:3000/jobs    |           |       |

---

## Heavy Resources

| Resource URL | Type   | Size  | Load Time | Action Needed |
|--------------|--------|-------|-----------|---------------|
|              |        |       |           |               |

---

## Slow API Requests

| Endpoint        | Method | Duration | Status | Notes |
|-----------------|--------|----------|--------|-------|
|                 |        |          |        |       |

---

## Unnecessary Requests

| URL | Reason Unnecessary | Recommendation |
|-----|--------------------|----------------|
|     |                    |                |

---

## JavaScript Issues
- [ ] Large unminified bundle
- [ ] Unused imports / dead code loaded
- [ ] Long task blocking main thread (>50ms)
- [ ] Render-blocking script

---

## CSS Issues
- [ ] Unused CSS loaded
- [ ] Large CSS file without purge
- [ ] Render-blocking stylesheet

---

## Image / Font Issues
- [ ] Uncompressed images
- [ ] Missing lazy loading
- [ ] Font not preloaded
- [ ] No fallback font

---

## Console Performance Warnings
```
[list any relevant console performance warnings]
```

---

## Lighthouse Scores (if run)

| Category       | Score |
|----------------|-------|
| Performance    |       |
| Accessibility  |       |
| Best Practices |       |
| SEO            |       |

---

## Recommendations

| # | Issue | Priority | Recommendation |
|---|-------|----------|----------------|
| 1 |       | High     |                |
| 2 |       | Medium   |                |

---

## Adoption / Action Status

> **[no action needed / optimize in v1.x / critical fix needed]**

---

## Notes
[Additional observations, comparison vs previous benchmark if any]
