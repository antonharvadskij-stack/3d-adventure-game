# AION agent discontinuity diagnosis and isolated Genesis prototype

## Safety boundary
- This branch starts from diagnostic commit `69524a8562e8aefc801e5a34bb4f8eba0970bb23`.
- This prototype is a standalone Node.js script with no third-party dependencies.
- It does not import the browser client, call a server, write PostgreSQL, mutate production, or execute Big Bang.
- Do not merge or deploy this branch as a production fix.

## Current evidence
The browser QA run `39623297955` failed at “Run browser smoke and movement/collision regression”; the isolated 120-second physics step passed. The browser harness samples the agent state before and after a 10-second interval. A large endpoint displacement proves the regression check failed, but by itself cannot distinguish a single teleport from a long path, an entity replacement with a reused ID, or intermediate oscillation.

The client `index.html` currently polls `loadAION()` every 5 seconds. In the same-world-version branch, the client updates metadata and intentionally does not reapply transforms. On a world-version change, incoming state is applied to a new generation. This is a diagnostic lead, not a confirmed root cause.

## Prototype
Run:

```sh
node qa/isolated_genesis_prototype.mjs
```

The deterministic baseline runs 8 agents for 120 simulated seconds at a fixed 1/60-second timestep. A separate controlled fault-injection run adds a 50-unit jump to one agent; the regression detector must catch it. The script asserts both outcomes and prints bounded telemetry.

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
