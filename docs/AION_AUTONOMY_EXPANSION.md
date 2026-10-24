# AION autonomy expansion — isolated sandbox plan

## Purpose

Expand AION from a fixed demo into an agent-driven Genesis simulation. Agents should be able to propose goals, make decisions, build and alter a world, observe consequences, and improve their own strategies. This document is a design contract for an isolated development branch; it does not claim these capabilities are already implemented.

## Autonomy model

### Phase 1 — self-directed decisions inside a disposable simulation

- Agents choose goals and actions without a hard-coded global action script.
- Each agent maintains a small, inspectable state: identity, goals, observations, resources, action history, and current plan.
- Agents can propose terrain, climate, vegetation, organisms, and social rules through explicit world-change intents.
- A deterministic simulation loop applies accepted intents and records before/after state.
- Agents can revise plans from observed outcomes and bounded feedback.
- Randomness is seeded and replayable so a run can be reproduced.

### Phase 2 — world construction

- Start with an empty world state, then let the Genesis coordinator and agents propose world features.
- Build terrain, water, climate, ecosystems, and organisms incrementally instead of replacing the entire world in one unobservable operation.
- Every generated feature has provenance: creator agent, input state, seed, tick, and resulting change.
- World changes are reversible within the sandbox through checkpoints and event history.
- The existing browser scene is a renderer, not the source of truth for simulation state.

### Phase 3 — bounded self-improvement

- Agents may propose edits to their own policies, prompts, parameters, and tools in a separate candidate version.
- Candidate versions run against deterministic regression suites and resource budgets.
- Compare candidate vs. baseline using explicit metrics: task success, stability, diversity, compute/time cost, and regression count.
- Promote a candidate only when it passes tests and has a measurable benefit; otherwise retain the baseline.
- No agent can silently rewrite the evaluator or remove the checks that decide whether its own candidate passes.

## Capability boundaries

The intent is to remove unnecessary fixed behavior inside the simulation, not to make the development environment unobservable or irreversible.

Allowed by default in this branch:
- arbitrary simulated world changes inside a disposable in-memory world;
- autonomous agent decisions and role formation;
- agent-proposed code/config changes as candidate patches;
- repeated seeded experiments and automatic rollback of failed candidates;
- increasing population and simulation complexity within configurable compute budgets.

Require a separate explicit operator decision:
- writes to shared or production databases;
- deployment to production or changes to external infrastructure;
- deletion or replacement of persistent worlds/data;
- publishing or merging changes to protected branches;
- granting agents external credentials or unrestricted network access.

These boundaries are not simulation restrictions: they keep experiments reversible and prevent a test agent from destroying the environment used to evaluate it.

## Implementation sequence

1. Add a pure simulation core with a seeded RNG, stable agent IDs, world state, and a tick loop.
2. Define a typed action/intent schema for movement, world generation, resource use, communication, and policy proposals.
3. Add an event log and checkpoints; make each tick replayable.
4. Implement an agent scheduler that gathers observations, evaluates goals, chooses actions, and records rationale/metrics.
5. Add Genesis world-generation intents and incremental terrain/ecosystem construction.
6. Add a candidate-policy sandbox and automated baseline-vs-candidate evaluation.
7. Add browser visualisation as a read-only view of the simulation and keep browser QA as a separate signal.
8. Only after deterministic tests and repeatable browser runs, consider integration into the live service.

## Acceptance criteria

- Same seed and same inputs produce the same simulation trace.
- Every agent has a stable identity independent of array order.
- A simulation can start from an empty world and generate world features through agent intents.
- Agents can alter goals and plans based on outcomes without editing the evaluator.
- Candidate self-modifications are isolated, measurable, and automatically discarded on regression.
- A checkpoint restores the exact prior simulation state.
- Physics and lifecycle regression tests pass repeatedly.
- No production, shared database, or external infrastructure changes are performed by sandbox tests.

## Current evidence and limitations

The browser trace diagnostics branch currently passes its latest physics and visual QA runs, but the previous large displacement has not been reproduced and its root cause remains unconfirmed. The existing isolated Genesis prototype is a deterministic physics detector test, not a complete autonomous world-generation system. This plan must not be described as already implemented until the code and tests exist.
