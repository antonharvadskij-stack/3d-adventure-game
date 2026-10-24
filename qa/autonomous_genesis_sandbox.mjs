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
    world: { terrain: [], biomes: [], organisms: [], events: [], ecology: [] },
    agents: Array.from({ length: agentCount }, (_, i) => ({
      id: \`genesis-agent-\${String(i + 1).padStart(3, '0')}\`,
      role: ['geologist', 'climatologist', 'botanist', 'ecologist'][i % 4],
      energy: 10 + Math.floor(random() * 6),
      goal: 'survey-empty-world',
      decisions: 0,
      goalChanges: 0,
    })),
    random,
  };
}

function observe(sim, agent) {
  const meanOrganismEnergy = sim.world.organisms.length
    ? sim.world.organisms.reduce((sum, o) => sum + o.energy, 0) / sim.world.organisms.length
    : 0;
  return {
    terrainCount: sim.world.terrain.length,
    biomeCount: sim.world.biomes.length,
    organismCount: sim.world.organisms.length,
    ownEnergy: agent.energy,
    meanOrganismEnergy,
    tick: sim.tick,
  };
}

function chooseGoal(agent, o) {
  // Goals are recalculated from current conditions, role and energy on every decision.
  if (o.ownEnergy <= 2) return 'recover-energy';
  if (o.terrainCount < 6 && agent.role === 'geologist') return 'shape-terrain';
  if (o.biomeCount < 5 && o.terrainCount >= 2 && agent.role === 'climatologist') return 'establish-biomes';
  if (o.organismCount < 12 && o.biomeCount > 0 && (agent.role === 'botanist' || agent.role === 'ecologist')) return 'seed-life';
  if (o.organismCount > 0 && o.meanOrganismEnergy < 2) return 'restore-ecosystem';
  if (o.biomeCount < 5 && o.terrainCount >= 2) return 'establish-biomes';
  if (o.organismCount < 12 && o.biomeCount > 0) return 'seed-life';
  if (o.terrainCount < 6) return 'shape-terrain';
  return 'stabilize-world';
}

function chooseIntent(sim, agent, observation) {
  if (agent.energy <= 2) return { type: 'recover-energy' };
  if (observation.terrainCount < 6 && (agent.role === 'geologist' || sim.random() < 0.18)) {
    return { type: 'create-terrain', kind: ['plain', 'hill', 'valley', 'ridge'][Math.floor(sim.random() * 4)] };
  }
  if (observation.biomeCount < 5 && observation.terrainCount >= 2 && (agent.role === 'climatologist' || sim.random() < 0.22)) {
    return { type: 'create-biome', kind: ['temperate', 'wetland', 'dryland', 'boreal'][Math.floor(sim.random() * 4)] };
  }
  if (observation.organismCount < 12 && observation.biomeCount > 0 && (agent.role === 'botanist' || agent.role === 'ecologist' || sim.random() < 0.24)) {
    return { type: 'create-organism', kind: ['moss', 'grass', 'shrub', 'grazer', 'pollinator'][Math.floor(sim.random() * 5)] };
  }
  if (observation.organismCount > 0 && observation.meanOrganismEnergy < 2) return { type: 'restore-ecosystem' };
  return { type: 'observe-and-replan' };
}

function applyIntent(sim, agent, intent, previousGoal) {
  const id = \`feature-\${String(sim.world.events.length + 1).padStart(4, '0')}\`;
  let outcome = 'plan-revised';
  if (intent.type === 'create-terrain') {
    sim.world.terrain.push({ id, kind: intent.kind, x: Math.floor(sim.random() * 101) - 50, z: Math.floor(sim.random() * 101) - 50 });
    outcome = 'terrain-created';
  } else if (intent.type === 'create-biome') {
    const terrain = sim.world.terrain[Math.floor(sim.random() * sim.world.terrain.length)];
    sim.world.biomes.push({ id, kind: intent.kind, terrainRef: terrain.id, fertility: 2 + Math.floor(sim.random() * 4) });
    outcome = 'biome-created';
  } else if (intent.type === 'create-organism') {
    const biome = sim.world.biomes[Math.floor(sim.random() * sim.world.biomes.length)];
    sim.world.organisms.push({ id, kind: intent.kind, biomeRef: biome.id, energy: 1 + Math.floor(sim.random() * 5) });
    outcome = 'organism-created';
  } else if (intent.type === 'restore-ecosystem') {
    for (const organism of sim.world.organisms) organism.energy = Math.min(8, organism.energy + 1);
    outcome = 'ecosystem-restored';
  }
  if (intent.type === 'recover-energy' || intent.type === 'observe-and-replan') agent.energy = Math.min(16, agent.energy + 2);
  else agent.energy = Math.max(0, agent.energy - 1);
  agent.decisions++;
  if (agent.goal !== previousGoal) agent.goalChanges++;
  sim.world.events.push({ tick: sim.tick, agentId: agent.id, role: agent.role, goal: agent.goal, intent: { ...intent }, outcome });
}

function applyEcologicalFeedback(sim) {
  // Simple bounded feedback: organisms gain energy in fertile biomes and lose it otherwise.
  let totalEnergy = 0;
  for (const organism of sim.world.organisms) {
    const biome = sim.world.biomes.find(b => b.id === organism.biomeRef);
    organism.energy = Math.max(0, Math.min(8, organism.energy + (biome && biome.fertility >= 3 ? 1 : -1)));
    totalEnergy += organism.energy;
  }
  sim.world.ecology.push({ tick: sim.tick, organisms: sim.world.organisms.length, totalEnergy });
}

function run(seed = 0xA10A, ticks = 80) {
  const sim = createSimulation(seed);
  for (let tick = 1; tick <= ticks; tick++) {
    sim.tick = tick;
    applyEcologicalFeedback(sim);
    // Rotate starting agent each tick to avoid array-order privilege.
    const offset = (tick - 1) % sim.agents.length;
    for (let n = 0; n < sim.agents.length; n++) {
      const agent = sim.agents[(offset + n) % sim.agents.length];
      const observation = observe(sim, agent);
      const oldGoal = agent.goal;
      agent.goal = chooseGoal(agent, observation);
      applyIntent(sim, agent, chooseIntent(sim, agent, observation), oldGoal);
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
assert.ok(a.agents.some(agent => agent.goalChanges > 0), 'agents should adapt goals as observations change');
assert.ok(a.world.ecology.length === a.tick, 'ecological feedback should run every tick');
assert.ok(a.world.ecology.some(e => e.totalEnergy > 0), 'ecosystem feedback should affect organism energy');
assert.ok(a.agents.every(agent => agent.energy >= 0 && agent.energy <= 16), 'agent energy must remain bounded');
console.log(JSON.stringify({
  result: 'PASS', prototype: 'autonomous-genesis-sandbox', seed: a.seed, ticks: a.tick,
  agents: a.agents.length, terrain: a.world.terrain.length, biomes: a.world.biomes.length,
  organisms: a.world.organisms.length, decisions: a.world.events.length,
  goalChanges: a.agents.reduce((sum, agent) => sum + agent.goalChanges, 0),
  ecologicalFeedbackTicks: a.world.ecology.length,
  deterministicReplay: true, persistence: 'disabled', network: 'disabled', productionChanges: 'none',
}, null, 2));
