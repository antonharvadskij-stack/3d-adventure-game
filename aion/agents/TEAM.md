# AION Agent Team — operating contract

## Goal
Run a controlled diagnose → propose fix → test → verify loop for the 3D Adventure Game. Agents are role-separated reviewers, not independent privileged identities. Each role must report evidence and uncertainty; the coordinator owns sequencing and stop conditions.

## Safety invariants
- Test target only: https://aion-server-test.onrender.com/
- Never deploy to production from this workflow.
- Never run BIG_BANG or destructive/reset/migration tasks.
- PostgreSQL is protected: no schema/data mutation, truncation, reset, or writes as part of QA.
- PR6 must not be merged by automation.
- Do not claim a root cause is confirmed without a reproducer and evidence.
- Do not turn a skipped test into a pass. Report PASS / FAIL / BLOCKED / SKIPPED separately.
- No agent may merge, deploy, change secrets, or bypass required reviews.

## Roles and required output
Every report includes: commit SHA, test target, evidence/artifact paths, observed facts, hypothesis (clearly labeled), confidence, and next action.

### 1. Coordinator
Creates one bounded task per cycle; assigns roles; tracks the candidate SHA; prevents concurrent conflicting edits; stops after two unsuccessful fix attempts and escalates with evidence. Only accepts a fix after independent QA and reviewer sign-off.

### 2. Diagnostics
Reproduces the failure on the test service; captures console/network/server symptoms and hydration warnings; distinguishes hydration mismatch from unrelated navigation aborts. Must not label the hydration root cause confirmed without a minimal reproduction or source-level proof.

### 3. Developer
Makes the smallest targeted change on a dedicated branch. Adds a regression test first where practical. Does not modify production configuration, protected database state, or unrelated systems. Explains why the change addresses the observed failure.

### 4. QA
Runs deterministic unit/integration/browser tests against the candidate commit. Checks regression coverage and reports exact commands, exit codes, and skipped checks. Never treats an unavailable test service as a pass.

### 5. Visual QA
Captures screenshots at documented viewport sizes and compares against the baseline. Reports layout, rendering, console, and hydration observations separately. Stores screenshots/reports as workflow artifacts when possible.

### 6. Reviewer
Reviews the diff for correctness, scope, security, performance, and test quality. Must be independent of the authoring step. Returns APPROVE or REQUEST_CHANGES with concrete evidence; cannot merge PR6.

## Test-fix-verify state machine
1. INSPECT: establish branch and SHA; inspect prior QA artifacts and latest workflow evidence.
2. DIAGNOSE: reproduce; record baseline and classify failure.
3. PLAN: write a falsifiable hypothesis and smallest safe patch.
4. IMPLEMENT: change isolated branch; add regression coverage.
5. TEST: run targeted test, then relevant regression suite.
6. VISUAL_VERIFY: capture/compare visual evidence where applicable.
7. REVIEW: independent diff review and safety check.
8. ACCEPT only when required checks are PASS and artifacts identify the exact candidate SHA. Otherwise return to DIAGNOSE or stop as BLOCKED.
9. REPORT: summarize changed files, evidence, remaining risks, and explicit deployment/merge status.

## Current checkpoint (2026-10-19)
- Agent workflow branch: aion/agent-team-workflows
- Latest candidate commit at checkpoint: 026d7a96f86257b64e40c6855d6a24b165599e10
- PR: #7, OPEN DRAFT, NOT MERGED
- Prior physics/visual CI PASS values belong to operator-supplied checkpoint f3343d4ae6b8a81a2718f2851f273daf2d0b74a6; they were not re-run against this candidate.
- Current candidate CI: NOT VERIFIED (no statuses reported; available run lookup found no PR-triggered runs and does not cover all events).
- Browser QA: patched to fail on HTTP 5xx and to report candidate SHA/test target; static file inspection only, runtime not executed/verified.
- Test service aion-server-test auto-deploys from aion-self-mechanics, with live commit 163741870743ec89b463258d4984f177353c043b at last deploy inspection. Browser test therefore combines candidate client with live test API.
- Latest read-only Render log queries returned no matching error or 500/502/503/504 request logs in the queried window; absence of log entries does not prove the endpoint is healthy.
- Hydration root cause: NOT CONFIRMED
- Safety: production DO NOT DEPLOY; PostgreSQL PROTECTED; BIG_BANG DO NOT RUN; PR6 DO NOT MERGE.
- Next: trigger the workflow through GitHub Actions UI, inspect the exact-SHA artifact, then decide whether a coordinated test-service revision is necessary.

## Current checkpoint (2026-10-20 — run #11 reviewed)
- Run #11: https://github.com/antonharvadskij-stack/3d-adventure-game/actions/runs/39277710376
- Artifact `aion-agent-qa-39277710376` was inspected directly; report candidate SHA is `1328fa87cb6660a93984b9f7f857b50b19b2ed9`.
- Report assertions were all green: hydration true at all three checkpoints; no recorded browser errors; world-age/cycle/version monotonicity true; no HTTP 5xx recorded.
- Important QA isolation defect found during source review: the browser route guard covered only the test origin, while `index.html` selects production API by default unless the exact `?server=https://aion-server-test.onrender.com` query parameter is present. The test page was opened without that query. The client schedules a POST to `/physics/colliders`; that request could therefore have reached production and would not appear in the test-origin-only `blockedMutations` list. Whether the production endpoint accepted it is NOT CONFIRMED from the artifact. Do not infer that production data changed; do treat the previous run as invalid for test-isolation assurance.
- Safety fix committed as `3dbf9ba41441e7934b31f10e7875d84b45ecb62d`: browser QA now adds the explicit test-server query parameter, globally blocks cross-origin requests, records forbidden production requests, and fails if any cross-origin request is attempted.
- Next: inspect the new push-triggered workflow/artifact for commit `3dbf9ba41441e7934b31f10e7875d84b45ecb62d`; confirm no production-origin requests and verify the browser lifecycle again.
- Deployment status unchanged: no production deployment, no merge, no PostgreSQL mutation, no BIG_BANG.
