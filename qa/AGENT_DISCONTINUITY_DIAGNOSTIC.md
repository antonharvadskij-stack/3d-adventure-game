# AION agent discontinuity diagnosis and isolated Genesis prototype

## Safety boundary
- This branch starts from diagnostic commit `69524a8562e8aefc801e5a34bb4f8eba0970bb23`.
- This prototype is a standalone Node.js script with no third-party dependencies.
- It does not import the browser client, call a server, write PostgreSQL, mutate production, or execute Big Bang.
- Do not merge or deploy this branch as a production fix.

## Current evidence
The browser QA run `39623297955` failed at “Run browser smoke and movement/collision regression”; the isolated 120-second physics step passed. The browser harness samples the agent state before and after a 10-second interval. A large endpoint displacement proves the regression check failed, but by itself cannot distinguish a single teleport from a long path, an entity replacement with a reused ID, or intermediate oscillation.

The client `index.html` currently polls `loadAION()` every 5 seconds. In the same-world-version branch, the client updates metadata and intentionally does not reapply transforms. On a world-version change, incoming state is applied to a new generation. This is a diagnostic lead, not a confirmed root cause.

## Artifact findings (run 39623297955)
The downloaded `aion-browser-qa` artifact confirms:
- Agent key `270`: from `(-51.205828, 0.163487, 77.144664)` to `(-19.394308, 2.434463, -101.996542)`, reported endpoint distance `181.958`.
- Reported max horizontal speed is `1.15`; the same world version `1564` and resident count `20` were observed before and after.
- The lifecycle artifact snapshots show server population IDs `263..282` in the same order across its three snapshots. This does not establish that order stayed stable during the separate 10-second physics interval.
- The QA compares snapshots by `String(a.serverId ?? a.name)`. The client assigns `serverId` by incoming array index in the same-world branch. This is a plausible identity-confounding risk and must be tested with a stable local instance ID before concluding a physical teleport occurred.
- The QA run's blocked POSTs to `/physics/colliders` were blocked by the harness; no unexpected mutation was reported.

## Prototype
Run:

```sh
node qa/isolated_genesis_prototype.mjs
```

The deterministic baseline runs 8 agents for 120 simulated seconds at a fixed 1/60-second timestep. A separate controlled fault-injection run adds a 50-unit jump to one agent; the regression detector must catch it. The script asserts both outcomes and prints bounded telemetry. The script logic was executed locally with Node.js: baseline passed all 7,200 ticks with zero faults; fault injection was detected at tick 600 (measured step 49.981, allowed 0.019267). This validates the isolated detector only, not the production browser simulation.

## Current next step: execute safe branch QA
The repository has two relevant workflows on this branch:
- `.github/workflows/aion-qa.yml` runs on every branch push. Its normal path runs isolated physics and browser QA against the test server; the PostgreSQL-backed persistence POST is guarded by `workflow_dispatch` plus an explicit boolean input and is not part of a push run.
- `.github/workflows/aion-visual-qa.yml` also runs on branch pushes and validates client syntax plus the browser smoke test against the test server.

Therefore, push a documentation-only update to this diagnostic branch to trigger normal QA, then inspect both workflow results and download the generated artifacts. Do not manually dispatch the persistence workflow, do not enable its live-persistence input, and do not deploy production.

When the new artifact is available:
1. Read `aion-physics-regression.json` fields `trajectorySampleCount`, `trajectoryFaultCount`, `firstTrajectoryFault`, and `noTeleport`.
2. If a first fault exists, correlate timestamp, stable `instanceId`, `serverId`, worldVersion, coordinates, and velocity before editing simulation code.
3. If no trajectory fault exists but endpoint displacement still fails, inspect identity matching and the sampling window before concluding there was a teleport.
4. Only patch a transform writer after evidence identifies the responsible code path; rerun QA and the isolated 120-second test.

## Stable-identity browser trace (isolated diagnostics branch)
The branch `aion/identity-trace-diagnostics-20261023` adds a read-only `instanceId` to each live client-agent object via a `WeakMap`. The ID is distinct from server-provided `serverId`, persists for the lifetime of that local object, and is not used to drive simulation behavior. The browser regression harness now samples transforms every 50 ms during its 10-second observation window and reports the first per-instance jump above the conservative per-sample threshold, including before/after server IDs, world versions, coordinates, velocities, and sample interval. The existing endpoint displacement check remains as a second signal.

Interpretation:
- If the endpoint displacement is large but no same-instance per-sample jump occurs, investigate the QA comparison window / sampling and trajectory path before calling it a teleport.
- If a large jump occurs while `instanceId` stays stable, inspect the first recorded sample's transform writers and world-version changes; this is evidence of a local transform discontinuity, not yet proof of which writer caused it.
- If `serverId` changes while `instanceId` remains stable, investigate incoming-population ordering and index-based metadata reassignment.
- This patch adds observation only. It does not fix simulation logic and must not be deployed as a production change.

## Acceptance criteria
- Baseline 120-second deterministic run passes.
- Injected discontinuity is detected and reports the offending agent and before/after coordinates.
- Actual browser regression has a captured first-fault trace and a confirmed responsible code path.
- Browser QA passes repeatedly with no teleport, invalid transforms, severe overlaps, or unexpected writes.
- No production deploy, PostgreSQL mutation, Big Bang execution, or PR6 merge is part of this task.
