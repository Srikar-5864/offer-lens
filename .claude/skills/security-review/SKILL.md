---
name: security-review
description: Apply and verify OfferLens security and maintenance controls (SGLang binding, prompt-injection defenses, FastAPI hardening, CSP-safe frontend, PII handling, supply-chain checks). Use after building the API or UI and before every demo or commit of a stage.
---

# Security review

Source of truth: `docs/SECURITY.md`. Walk this checklist and fix anything failing; don't just report it.

## Automated
```bash
make check                                      # ruff, mypy, pytest, bandit, pip-audit, gitleaks
grep -rn "0.0.0.0" Makefile configs src         # must be empty
grep -rn "innerHTML\|eval(\|new Function" web   # must be empty
grep -rn "trust_remote_code=True" src           # must be empty
git ls-files | grep -E "\.env$|data/real|models/" # must be empty
```

## Manual (with the app running)
- `curl -sI http://127.0.0.1:8000/` → CSP, nosniff, Referrer-Policy, Permissions-Policy present.
- POST 2,500-char text → 422 with friendly message. POST 9 KB body → 413.
- 40 quick requests → 429 after 30.
- Injection inputs (the `injection` demo example + tests/fixtures/injection.jsonl) → output is still schema JSON, no echoed instructions.
- Offer text containing `<script>alert(1)</script>` → rendered as literal text in the UI.
- `/docs` returns 404 when `ENV != dev`.
- Logs contain hashes, not raw offer text.

## Tests that must exist
`tests/test_api.py`: size limits, headers, problem+json errors, invalid model output → `valid:false` (SGLang mocked).
`tests/test_schema.py`: validators (percent ≤ 100, date order, coupon regex, extra fields forbidden).
