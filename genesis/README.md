# AION Genesis — isolated VOID prototype

This directory is a deliberately separate, dependency-free prototype. It does not import the live game, connect to PostgreSQL, call production APIs, or mutate existing worlds.

## Model

- **VOID** is the initial state: no terrain, organisms, or world objects.
- **God AI** is represented as a bounded proposal/planning function, not an unrestricted executor.
- **Agents** are stateful entities with stable IDs, bounded movement, and deterministic updates.
- **World creation** is a sequence of explicit events (terrain, climate, organisms, structures); every event is validated before application.
- **Self-development** is represented by proposals to change a versioned rule set. Proposals are sandboxed and require deterministic checks before they can be accepted.

## Run

```sh
node genesis/void-sim.mjs
node --test genesis/void-sim.test.mjs
```

No package installation is required (Node.js built-ins only).

## Safety boundaries

The prototype is offline and in-memory. It cannot deploy, access credentials, contact external services, or modify production data. It intentionally does not implement real model autonomy, self-modifying executable code, or a destructive "big bang". It is a testable simulation of governance and emergence primitives.

## Browser discontinuity investigation

The current browser report is evidence of a discontinuity, not a confirmed root cause. The QA samples before and after a 10-second interval and compares matching IDs. Next diagnosis must log per-agent stable identity, sample timestamps, position and velocity at every sample, server/client authority, world/session version, and any spawn/respawn/teleport/correction events. Check whether ID 270's identity remains attached to the same entity and coordinate frame. Do not weaken the no-teleport assertion to make QA green.
