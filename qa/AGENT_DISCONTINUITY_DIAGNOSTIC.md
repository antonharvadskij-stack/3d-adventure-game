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

## Next investigation against browser QA
1. Download artifact `aion-browser-qa` from run `39623297955` and read `aion-physics-regression.json` to capture agent 270's actual `from` and `to` transforms.
2. Inspect `index.html` for every write to `a.g.position`, every `serverId` assignment, and every code path that clears/rebuilds `agents`.
3. Add opt-in, read-only telemetry at each transform writer: monotonic timestamp, agent ID and object identity, worldVersion, old/new xyz, velocity, delta time, caller/reason.
4. Run the browser test with per-tick trajectory samples and correlate the first discontinuity with poll/hydration timestamps. Do not infer the cause from endpoint displacement alone.
5. Fix only after a minimal reproduction proves the responsible writer; rerun isolated physics and browser QA repeatedly.

## Acceptance criteria
- Baseline 120-second deterministic run passes.
- Injected discontinuity is detected and reports the offending agent and before/after coordinates.
- Actual browser regression has a captured first-fault trace and a confirmed responsible code path.
- Browser QA passes repeatedly with no teleport, invalid transforms, severe overlaps, or unexpected writes.
- No production deploy, PostgreSQL mutation, Big Bang execution, or PR6 merge is part of this task.
