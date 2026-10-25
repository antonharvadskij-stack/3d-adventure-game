# AION autonomy expansion — isolated sandbox plan

## Purpose

Expand AION from a fixed demo into an agent-driven Genesis simulation. Agents should make decisions from observations, build and alter a world, observe consequences, and eventually improve their own strategies. Work is isolated on this branch; the live browser simulation is unchanged.

## Implemented prototype

File: `qa/autonomous_genesis_sandbox.mjs`

Run with Node.js:

```sh
node qa/autonomous_genesis_sandbox.mjs
```

Current prototype:
- starts with an empty in-memory world;
- runs 8 stable-ID agents with distinct roles across 80 ticks;
- recalculates agent goals from current observations, role, and energy (including recovery and world-stabilization goals);
- lets role-aware policies choose terrain, biome, organism, ecosystem-restoration, or observe/replan intents from current world observations;
- applies bounded ecological feedback every tick: organisms gain energy in fertile biomes and lose energy otherwise;
- exchanges bounded peer messages carrying world-state signals between agents of different roles;
- collects one structured intent proposal per agent before mutating the world;
- validates world references, then resolves same-type world-change conflicts by explicit priority and stable agent ID;
- journals each proposal with provenance, priority, resource cost, acceptance status, and a deterministic resolution reason;
- gives each agent a bounded resource budget (0–8 units), regenerates one unit per tick, and charges resources only for accepted world-changing intents;
- records an explicit acknowledgement for every proposal, including accepted/rejected status, reason, and before/after resource balance;
- runs a negotiation phase in which peer signals endorse compatible biome, life, or ecosystem-restoration proposals;
- gives each agent a dependency-aware Genesis plan with stages for terrain, then biomes, then organisms; stages advance only when the observed world meets the stage target;
- records each proposal's plan step and exposes per-agent plan-stage advancement metrics;
- counts plan retries by explicit rejection reason (conflict, resource exhaustion, or invalid world reference), making blocked work inspectable;
- after repeated plan blocks, proposes a different currently valid and affordable action (when available), excluding the last blocked action type; alternatives still pass the normal reference validation, conflict arbitration, and resource charging path;
- counts fallback actions per agent so recovery behavior can be measured in deterministic runs;
- runs a paired baseline-versus-recovery ablation over 10 fixed seeds and reports both aggregate means and per-seed outcomes for world growth, survival, the heuristic stability score, plan completion, retries, fallback use, and resource expenditure;
- records a post-resolution world-quality snapshot each tick with terrain/biome/organism counts, biome-kind diversity, living-organism ratio, mean organism energy, a bounded ecosystem-stability score, and dependency integrity;
- uses observed low organism survival or ecosystem-stress messages to prioritize restoration actions;
- records endorsements and negotiated priorities, caps the influence of endorsements, and uses stable agent IDs for deterministic tie-breaking; negotiation cannot bypass world validation or resource budgets;
- tests resource bounds, acknowledgement coverage, and deterministic resource-budget rejection accounting;
- lets received peer signals influence goal selection (e.g. biome needs, life needs, ecosystem stress);
- records the agent, tick, intent, and outcome for every decision;
- builds terrain, biomes, and organisms incrementally;
- uses a seeded RNG and asserts that two identical runs produce the same trace;
- checks identity uniqueness, event provenance, organism-to-biome references, goal adaptation, bounded agent energy and resource budgets, ecological-feedback execution, valid communication sender/recipient identities, proposal/negotiation/acknowledgement accounting, valid endorsements and negotiated priorities, resolution reasons, and exact checkpoint restoration plus deterministic mid-run replay;
- reports goal-change, ecology, retry-reason, and world-quality metrics in its test output;
- asserts quality metric bounds, dependency integrity, retry accounting, and that the final quality snapshot describes the resolved world;
- has no network, persistence, production imports, or external side effects.

**Important limitation:** this is still a deterministic heuristic/role-policy prototype, not yet an LLM-driven agent society, a full 3D terrain generator, or a self-modifying code system. Dynamic goals and ecological feedback are deliberately simplified; the passing test demonstrates deterministic sandbox behavior, not open-ended intelligence.

## Autonomy model

### Phase 1 — self-directed decisions inside a disposable simulation

- Replace the initial role heuristics with agents that evaluate goals and competing actions from observations.
- Give each agent inspectable state: identity, goals, observations, resources, action history, and current plan.
- Support terrain, climate, vegetation, organisms, and social-rule proposals through explicit world-change intents.
- Apply intents through a deterministic simulation loop and record before/after state.
- Allow plans to change based on outcomes and bounded feedback.
- Keep randomness seeded and replayable.

### Phase 2 — world construction

- Start from an empty world state and let the Genesis coordinator and agents propose features.
- Build terrain, water, climate, ecosystems, and organisms incrementally.
- Record provenance for every feature: creator, input state, seed, tick, and resulting change.
- Support checkpoints and event replay so sandbox changes are reversible.
- Treat the browser scene as a renderer, not the source of truth for simulation state.

### Phase 3 — bounded self-improvement

- Let agents propose edits to their policies, prompts, parameters, and tools in candidate versions.
- Run candidates against deterministic regression suites and resource budgets.
- Compare candidates with baseline on task success, stability, diversity, compute/time cost, and regression count.
- Promote only a candidate that passes tests and provides a measurable benefit; otherwise keep the baseline.
- Do not allow an agent to silently rewrite the evaluator used to judge its own candidate.

## Capability boundaries

The goal is to remove unnecessary fixed behavior inside the simulation, not to make the development environment unobservable or irreversible.

Allowed by default in this branch:
- simulated world changes inside a disposable in-memory world;
- autonomous decision policies and role formation;
- candidate code/config changes in the isolated branch;
- repeated seeded experiments and rollback of failed candidates;
- increasing simulated population and complexity within configurable compute budgets.

Require a separate explicit operator decision:
- writes to shared or production databases;
- production deployment or changes to external infrastructure;
- deletion or replacement of persistent worlds/data;
- publishing or merging changes to protected branches;
- granting agents external credentials or unrestricted network access.

These boundaries keep experiments reversible; they do not constrain what agents can create inside the sandbox.

## Next implementation steps

1. Introduce a typed action schema for movement, world generation, resource use, communication, and policy proposals.
2. Extend proposal arbitration to multi-round negotiation, dependency-aware multi-step plans, and shared-resource coordination; current endorsements are a bounded first negotiation phase, not full deliberation.
3. Extend checkpoint coverage to long-running simulations and injected failures, then verify restoration and deterministic replay.
4. Upgrade the current sequential world targets into explicit dependency graphs with plan completion criteria; retry accounting and blocked-step reasons are recorded, while dependency scheduling remains a simple ordered sequence.
5. Run a paired 10-seed, 80-tick baseline-versus-recovery ablation with identical seeds; report mean world counts, living-organism ratio, heuristic stability score, completed plans, retries, alternative actions, and resource spend. Interpret it as a small deterministic experiment, not proof of general intelligence.
6. Add a scheduler for goal evaluation, action selection, rationale, and metrics.
7. Add generated terrain geometry and climate/ecosystem simulation.
8. Add candidate-policy execution in a separate process with time, memory, and filesystem limits.
9. Add baseline-vs-candidate evaluation and automatic rollback on regression.
10. Connect the browser only as a read-only view after simulation tests are stable.

## Acceptance criteria

- Same seed and same inputs produce an identical simulation trace.
- Every agent has a stable identity independent of array order.
- An empty world can gain terrain, biomes, and organisms through agent intents.
- Every world event has provenance and valid references.
- Agents can change goals/plans from observed outcomes without changing their evaluator.
- A checkpoint restores the exact prior state.
- Candidate self-modifications are isolated, measurable, and discarded on regression.
- Physics and lifecycle QA pass repeatedly before any integration into the live service.

## Current evidence and limitations

The browser trace diagnostics branch passed its latest physics and visual QA runs, but the earlier large displacement has not been reproduced and its root cause remains unconfirmed. The new Genesis sandbox prototype is an initial autonomous-world construction experiment; it does not replace the existing browser simulation and has not been deployed. No shared database or production infrastructure was changed.
