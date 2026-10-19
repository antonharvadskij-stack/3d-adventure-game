---
name: AION Browser QA
description: Tests AION browser hydration, lifecycle, rendering hooks, movement, collisions, and API safety.
---

Run Playwright tests from `qa/` with `AION_CLIENT_URL` explicitly targeting `aion-server-test.onrender.com`. Verify `window.__AION_SYNCED`, server state, and `window.__AION_QA.snapshot` before declaring hydration successful. Preserve screenshots and lifecycle reports on failures. Ignore request aborts only when the failure code confirms navigation cancellation. Keep real HTTP 5xx responses and JavaScript exceptions as failures. Verify non-GET/HEAD/OPTIONS requests are blocked before network access.

Do not target production or bypass mutation guards. Never modify PostgreSQL, run BIG_BANG, or merge PR #6.
