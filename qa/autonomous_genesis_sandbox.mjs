#!/usr/bin/env node
/**
 * AION autonomous Genesis sandbox: deterministic, in-memory, no network or persistence.
 * Run: node qa/autonomous_genesis_sandbox.mjs
 */
import assert from 'node:assert/strict';

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 0x100000000);
}

function createSimulation(seed = 0xA10A, agentCount = 8) {
  const random = rng(seed);
  return {
    seed, tick: 0,
    world: { terrain: [], biomes: [], organisms: [], events: [] },
    agents: Array.from({ length: agentCount }, (_, i) => ({
      id: `genesis-agent-${String(i + 1).padStart(3, '0')}`,
      role: ['geologist', 'climatologist', 'botanist', 'ecologist'][i % 4],
      energy: 10 + Math.floor(random() * 6),
      goal: 'create-a-living-world',
      decisions: 0,
    })),
    random,
  };
}

function observe(sim, agent) {
  return {
    terrainCount: sim.world.terrain.length,
    biomeCount: sim.world.biomes.length,
    organismCount: sim.world.organisms.length,
    ownEnergy: agent.energy,
    tick: sim.tick,
  };
}

function chooseIntent(sim, agent, observation) {
  // A role-aware local policy chooses actions from observations, not a global build script.
  if (observation.terrainCount < 6 && (agent.role === 'geologist' || sim.random() < 0.22)) {
    return { type: 'create-terrain', kind: ['plain', 'hill', 'valley', 'ridge'][Math.floor(sim.random() * 4)] };
  }
  if (observation.biomeCount < 5 && observation.terrainCount >= 2 && (agent.role === 'climatologist' || sim.random() < 0.28)) {
    return { type: 'create-biome', kind: ['temperate', 'wetland', 'dryland', 'boreal'][Math.floor(sim.random() * 4)] };
  }
  if (observation.organismCount < 12 && observation.biomeCount > 0 && (agent.role === 'botanist' || agent.role === 'ecologist' || sim.random() < 0.3)) {
    return { type: 'create-organism', kind: ['moss', 'grass', 'shrub', 'grazer', 'pollinator'][Math.floor(sim.random() * 5)] };
  }
  return { type: 'observe-and-replan' };
}

function applyIntent(sim, agent, intent) {
  const id = `${intent.type.split('-')[1] ?? 'event'}-${String(sim.world.events.length + 1).padStart(4, '0')}`;
  if (intent.type === 'create-terrain') sim.world.terrain.push({ id, kind: intent.kind, x: Math.floor(sim.random() * 101) - 50, z: Math.floor(sim.random() * 101) - 50 });
  else if (intent.type === 'create-biome') sim.world.biomes.push({ id, kind: intent.kind, terrainRef: sim.world.terrain[Math.floor(sim.random() * sim.world.terrain.length)].id });
  else if (intent.type === 'create-organism') sim.world.organisms.push({ id, kind: intent.kind, biomeRef: sim.world.biomes[Math.floor(sim.random() * sim.world.biomes.length)].id, energy: 1 + Math.floor(sim.random() * 5) });
  agent.decisions++;
  agent.energy = Math.max(0, agent.energy - (intent.type === 'observe-and-replan' ? 0 : 1));
  sim.world.events.push({ tick: sim.tick, agentId: agent.id, intent: { ...intent }, outcome: intent.type === 'observe-and-replan' ? 'plan-revised' : 'world-feature-created' });
}

function run(seed = 0xA10A, ticks = 80) {
  const sim = createSimulation(seed);
  for (let tick = 1; tick <= ticks; tick++) {
    sim.tick = tick;
    // Rotate starting agent each tick to avoid array-order privilege.
    const offset = (tick - 1) % sim.agents.length;
    for (let n = 0; n < sim.agents.length; n++) {
      const agent = sim.agents[(offset + n) % sim.agents.length];
      const observation = observe(sim, agent);
      applyIntent(sim, agent, chooseIntent(sim, agent, observation));
    }
  }
  const { random, ...serializable } = sim;
  return serializable;
}

const a = run(20261024, 80);
const b = run(20261024, 80);
assert.deepEqual(a, b, 'same seed must produce an identical trace');
assert.equal(a.agents.length, 8);
assert.equal(new Set(a.agents.map(x => x.id)).size, a.agents.length, 'agent identities must be unique');
assert.ok(a.world.terrain.length > 0, 'Genesis should create terrain from an empty world');
assert.ok(a.world.biomes.length > 0, 'Genesis should create biomes from agent intents');
assert.ok(a.world.organisms.length > 0, 'Genesis should create organisms from agent intents');
assert.ok(a.world.events.every(e => a.agents.some(agent => agent.id === e.agentId)), 'every event must have provenance');
assert.ok(a.world.organisms.every(o => a.world.biomes.some(biome => biome.id === o.biomeRef)), 'organisms must reference existing biomes');
console.log(JSON.stringify({
  result: 'PASS', prototype: 'autonomous-genesis-sandbox', seed: a.seed, ticks: a.tick,
  agents: a.agents.length, terrain: a.world.terrain.length, biomes: a.world.biomes.length,
  organisms: a.world.organisms.length, decisions: a.world.events.length,
  deterministicReplay: true, persistence: 'disabled', network: 'disabled', productionChanges: 'none',
}, null, 2));
