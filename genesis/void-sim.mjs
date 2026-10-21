#!/usr/bin/env node
/**
 * AION Genesis: tiny, offline-only emergence prototype.
 * No network, filesystem writes, database access, or production imports.
 */
export const GENESIS_VERSION = "0.1.0";
export const LIMITS = Object.freeze({
  maxAgents: 64,
  maxStep: 0.25,
  maxCoordinate: 10000,
  maxEventsPerTick: 8,
});

export function createGenesis(seed = 1) {
  if (!Number.isSafeInteger(seed)) throw new TypeError("seed must be a safe integer");
  return {
    version: GENESIS_VERSION,
    phase: "VOID",
    tick: 0,
    seed: seed >>> 0,
    rulesVersion: 1,
    terrain: [],
    climate: null,
    organisms: [],
    structures: [],
    agents: [],
    events: [],
    proposals: [],
  };
}

function random(state) {
  // Small deterministic PRNG; state mutation is explicit and reproducible.
  state.seed = (Math.imul(state.seed, 1664525) + 1013904223) >>> 0;
  return state.seed / 0x100000000;
}

export function proposeWorldEvent(state, event) {
  if (!state || state.phase === "RUNNING") throw new Error("world events require a paused Genesis state");
  const allowed = new Set(["CREATE_TERRAIN", "SET_CLIMATE", "SPAWN_ORGANISM", "BUILD_STRUCTURE", "SPAWN_AGENT"]);
  if (!event || !allowed.has(event.type)) throw new TypeError("unsupported Genesis event");
  if (state.proposals.length >= LIMITS.maxEventsPerTick * 4) throw new Error("proposal budget exceeded");
  const proposal = { id: state.proposals.length + 1, rulesVersion: state.rulesVersion, event: structuredClone(event), status: "PENDING" };
  state.proposals.push(proposal);
  return proposal;
}

export function validateEvent(state, event) {
  if (!event || typeof event !== "object") return { ok: false, reason: "event must be an object" };
  const numberInRange = n => Number.isFinite(n) && Math.abs(n) <= LIMITS.maxCoordinate;
  switch (event.type) {
    case "CREATE_TERRAIN":
      return numberInRange(event.extent) && event.extent > 0
        ? { ok: true } : { ok: false, reason: "terrain extent must be finite, positive, and bounded" };
    case "SET_CLIMATE":
      return Number.isFinite(event.temperature) && event.temperature >= -100 && event.temperature <= 100
        ? { ok: true } : { ok: false, reason: "temperature outside safe simulation bounds" };
    case "SPAWN_ORGANISM":
      return typeof event.species === "string" && event.species.trim().length > 0 && event.species.length <= 64
        ? { ok: true } : { ok: false, reason: "species must be a non-empty short label" };
    case "BUILD_STRUCTURE":
      return typeof event.kind === "string" && event.kind.length > 0 && event.kind.length <= 64
        ? { ok: true } : { ok: false, reason: "structure kind is invalid" };
    case "SPAWN_AGENT":
      return state.agents.length < LIMITS.maxAgents && numberInRange(event.x ?? 0) && numberInRange(event.z ?? 0)
        ? { ok: true } : { ok: false, reason: "agent capacity or coordinates invalid" };
    default:
      return { ok: false, reason: "unknown event type" };
  }
}

export function applyProposal(state, proposalId) {
  const proposal = state.proposals.find(p => p.id === proposalId);
  if (!proposal || proposal.status !== "PENDING") throw new Error("pending proposal not found");
  if (proposal.rulesVersion !== state.rulesVersion) {
    proposal.status = "REJECTED";
    proposal.reason = "stale rules version";
    return proposal;
  }
  const validation = validateEvent(state, proposal.event);
  if (!validation.ok) {
    proposal.status = "REJECTED";
    proposal.reason = validation.reason;
    return proposal;
  }
  const event = proposal.event;
  switch (event.type) {
    case "CREATE_TERRAIN": state.terrain.push({ extent: event.extent, kind: event.kind ?? "plain" }); break;
    case "SET_CLIMATE": state.climate = { temperature: event.temperature }; break;
    case "SPAWN_ORGANISM": state.organisms.push({ species: event.species, count: 1 }); break;
    case "BUILD_STRUCTURE": state.structures.push({ kind: event.kind }); break;
    case "SPAWN_AGENT":
      state.agents.push({ id: `agent-${state.agents.length + 1}`, x: event.x ?? 0, z: event.z ?? 0, vx: 0, vz: 0 });
      break;
  }
  state.events.push({ tick: state.tick, type: event.type, proposalId });
  state.phase = "EMERGING";
  proposal.status = "ACCEPTED";
  return proposal;
}

/** God AI is a constrained proposer: it can suggest events, never bypass validation. */
export function godAiStep(state) {
  if (state.phase === "RUNNING") throw new Error("pause simulation before world-design proposals");
  if (state.terrain.length === 0) return proposeWorldEvent(state, { type: "CREATE_TERRAIN", extent: 100, kind: "seeded-ground" });
  if (!state.climate) return proposeWorldEvent(state, { type: "SET_CLIMATE", temperature: 18 });
  if (state.organisms.length === 0) return proposeWorldEvent(state, { type: "SPAWN_ORGANISM", species: "pioneer" });
  if (state.agents.length === 0) return proposeWorldEvent(state, { type: "SPAWN_AGENT", x: 0, z: 0 });
  return proposeWorldEvent(state, { type: "BUILD_STRUCTURE", kind: "observation-hut" });
}

/** One deterministic, bounded tick; movement is clamped and IDs never change. */
export function tickGenesis(state) {
  if (state.phase === "VOID") throw new Error("cannot tick an empty VOID; accept a world event first");
  state.phase = "RUNNING";
  state.tick += 1;
  for (const agent of state.agents) {
    const dx = (random(state) - 0.5) * 2;
    const dz = (random(state) - 0.5) * 2;
    const length = Math.hypot(dx, dz) || 1;
    agent.vx = dx / length * LIMITS.maxStep;
    agent.vz = dz / length * LIMITS.maxStep;
    agent.x += agent.vx;
    agent.z += agent.vz;
    if (![agent.x, agent.z, agent.vx, agent.vz].every(Number.isFinite) ||
        Math.abs(agent.x) > LIMITS.maxCoordinate || Math.abs(agent.z) > LIMITS.maxCoordinate) {
      throw new Error(`invalid transform for ${agent.id}`);
    }
  }
  return state;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const state = createGenesis(20261021);
  for (let i = 0; i < 4; i++) {
    const proposal = godAiStep(state);
    applyProposal(state, proposal.id);
  }
  tickGenesis(state);
  console.log(JSON.stringify({ version: state.version, phase: state.phase, tick: state.tick,
    terrain: state.terrain.length, climate: state.climate, organisms: state.organisms.length,
    agents: state.agents, events: state.events }, null, 2));
}
