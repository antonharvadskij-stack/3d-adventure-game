# AION Agent Team

The repository defines specialist roles in `.github/agents/*.agent.md` and an executable parallel verification pipeline in `.github/workflows/aion-agent-team.yml`.

## Roles
- **Coordinator** — assigns the next safe task, combines evidence, and reports the exact commit and unresolved risks.
- **Diagnostic** — examines CI logs/artifacts and distinguishes hydration failures from transient HTTP 5xx, JS errors, and expected navigation aborts.
- **Physics QA** — runs deterministic and 120-second isolated PyBullet regression tests.
- **Browser QA** — validates hydration, lifecycle, movement/collisions, and read-only API safety using Playwright.
- **Reviewer** — independently reviews the diff and rejects tests that hide genuine errors.

## Safety invariants
- Only the feature branch and the isolated AION test service are in scope.
- Production deploys are prohibited.
- PostgreSQL is protected and must not be modified.
- Never run BIG_BANG.
- Never merge PR #6.
- Do not call a defect fixed unless the regression reproduces the defect before the fix and passes after it.
- Browser test routes must block mutating HTTP methods before any network request reaches the server.

## Current baseline
Latest inspected CI commit: `f3343d4ae6b8a81a2718f2851f273daf2d0b74a6`.
Both existing AION QA and AION Visual QA workflows completed successfully at that SHA. Their reports show successful hydration and physics/browser checks, but the diagnostic agent must still investigate any explicit transient-502 signal rather than assume all historical issues are resolved.
