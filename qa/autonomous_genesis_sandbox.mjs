#!/usr/bin/env node
/**
 * AION autonomous Genesis sandbox: deterministic, in-memory, no network or persistence.
 * Run: node qa/autonomous_genesis_sandbox.mjs
 */
import assert from 'node:assert/strict';

function rng(seed) {
  let s = seed >>> 0;
  const next = () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 0x100000000);
  next.getState = () => s;
  next.setState = state => { s = state >>> 0; };
  return next;
}

function createSimulation(seed = 0xA10A, agentCount = 8) {
  const random = rng(seed);
  return {
    seed, tick: 0,
    world: { terrain: [], biomes: [], organisms: [], events: [], ecology: [], messages: [], proposals: [] },
    agents: Array.from({ length: agentCount }, (_, i) => ({
      id: `genesis-agent-${String(i + 1).padStart(3, '0')}`,
      role: ['geologist', 'climatologist', 'botanist', 'ecologist'][i % 4],
      energy: 10 + Math.floor(random() * 6),
      goal: 'survey-empty-world',
      decisions: 0,
      goalChanges: 0,
      inbox: [],
      messagesSent: 0,
    })),
    random,
  };
}

function createCheckpoint(sim) {
  return {
    seed: sim.seed,
    tick: sim.tick,
    world: structuredClone(sim.world),
    agents: structuredClone(sim.agents),
    randomState: sim.random.getState(),
  };
}

function restoreCheckpoint(sim, checkpoint) {
  sim.seed = checkpoint.seed;
  sim.tick = checkpoint.tick;
  sim.world = structuredClone(checkpoint.world);
  sim.agents = structuredClone(checkpoint.agents);
  sim.random.setState(checkpoint.randomState);
}

function checkpointState(sim) {
  const { random, ...state } = sim;
  return { ...structuredClone(state), randomState: random.getState() };
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
  // Goals are recalculated from current conditions, role, energy, and peer reports.
  const peerSignals = agent.inbox.slice(-4).map(message => message.signal);
  if (o.ownEnergy <= 2) return 'recover-energy';
  if (peerSignals.includes('ecosystem-stress') && o.organismCount > 0) return 'restore-ecosystem';
  if (peerSignals.includes('need-biomes') && o.terrainCount >= 2 && o.biomeCount < 5) return 'establish-biomes';
  if (peerSignals.includes('need-life') && o.biomeCount > 0 && o.organismCount < 12) return 'seed-life';
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
  const id = `feature-${String(sim.world.events.length + 1).padStart(4, '0')}`;
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

function communicate(sim, sender) {
  const signal = sender.energy <= 2
    ? 'agent-needs-energy'
    : sim.world.organisms.length > 0 && sim.world.organisms.reduce((sum, o) => sum + o.energy, 0) / sim.world.organisms.length < 2
      ? 'ecosystem-stress'
      : sim.world.biomes.length < 5 && sim.world.terrain.length >= 2
        ? 'need-biomes'
        : sim.world.organisms.length < 12 && sim.world.biomes.length > 0
          ? 'need-life'
          : 'world-progress';
  const recipients = sim.agents.filter(agent => agent.id !== sender.id && agent.role !== sender.role);
  if (!recipients.length) return;
  const recipient = recipients[Math.floor(sim.random() * recipients.length)];
  const message = {
    tick: sim.tick, from: sender.id, to: recipient.id,
    signal, snapshot: {
      terrain: sim.world.terrain.length,
      biomes: sim.world.biomes.length,
      organisms: sim.world.organisms.length,
    },
  };
  sim.world.messages.push(message);
  recipient.inbox.push(message);
  if (recipient.inbox.length > 12) recipient.inbox.shift();
  sender.messagesSent++;
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

function stepSimulation(sim, tick) {
    sim.tick = tick;
    applyEcologicalFeedback(sim);
    // Rotate starting agent each tick to avoid array-order privilege.
    const offset = (tick - 1) % sim.agents.length;
    const proposals = [];
    for (let n = 0; n < sim.agents.length; n++) {
      const agent = sim.agents[(offset + n) % sim.agents.length];
      const observation = observe(sim, agent);
      communicate(sim, agent);
      const oldGoal = agent.goal;
      agent.goal = chooseGoal(agent, observation);
      const intent = chooseIntent(sim, agent, observation);
      // Proposals are recorded before any world mutation, so every agent in this
      // round competes against the same pre-resolution world state.
      const priority = intent.type === 'create-terrain' && observation.terrainCount < 6 ? 100
        : intent.type === 'create-biome' && observation.biomeCount < 5 ? 80
        : intent.type === 'restore-ecosystem' ? 90
        : intent.type === 'create-organism' && observation.organismCount < 12 ? 60
        : intent.type === 'recover-energy' ? 50 : 10;
      proposals.push({ tick: sim.tick, agentId: agent.id, role: agent.role, goal: agent.goal,
        intent, previousGoal: oldGoal, priority, observation });
    }
    // One winning world mutation per intent class per tick. Priority resolves
    // competing needs; stable agent ID breaks ties and makes replay deterministic.
    proposals.sort((x, y) => y.priority - x.priority || x.agentId.localeCompare(y.agentId));
    const claimed = new Set();
    for (const proposal of proposals) {
      const worldMutation = ['create-terrain', 'create-biome', 'create-organism', 'restore-ecosystem'].includes(proposal.intent.type);
      const conflictKey = worldMutation ? proposal.intent.type : null;
      const valid = proposal.intent.type !== 'create-biome' || sim.world.terrain.length > 0
        ? proposal.intent.type !== 'create-organism' || sim.world.biomes.length > 0
        : false;
      const accepted = valid && (!conflictKey || !claimed.has(conflictKey));
      sim.world.proposals.push({ tick: proposal.tick, agentId: proposal.agentId,
        intent: { ...proposal.intent }, priority: proposal.priority, accepted,
        reason: !valid ? 'invalid-world-reference' : accepted ? 'selected-by-priority-and-stable-id' : 'conflict-lost' });
      if (accepted) {
        if (conflictKey) claimed.add(conflictKey);
        applyIntent(sim, sim.agents.find(agent => agent.id === proposal.agentId), proposal.intent, proposal.previousGoal);
      } else {
        const agent = sim.agents.find(item => item.id === proposal.agentId);
        applyIntent(sim, agent, { type: 'observe-and-replan' }, proposal.previousGoal);
      }
    }
}

function run(seed = 0xA10A, ticks = 80) {
  const sim = createSimulation(seed);
  for (let tick = 1; tick <= ticks; tick++) stepSimulation(sim, tick);
  const { random, ...serializable } = sim;
  return serializable;
}

const checkpointProbe = createSimulation(20261024);
for (let tick = 1; tick <= 12; tick++) stepSimulation(checkpointProbe, tick);
const checkpoint = createCheckpoint(checkpointProbe);
for (let tick = 13; tick <= 24; tick++) stepSimulation(checkpointProbe, tick);
const uninterruptedAfterCheckpoint = checkpointState(checkpointProbe);
restoreCheckpoint(checkpointProbe, checkpoint);
assert.deepEqual(checkpointState(checkpointProbe), checkpoint, 'checkpoint must restore the exact simulation state');
for (let tick = 13; tick <= 24; tick++) stepSimulation(checkpointProbe, tick);
assert.deepEqual(checkpointState(checkpointProbe), uninterruptedAfterCheckpoint,
  'resuming from checkpoint must match uninterrupted execution exactly');

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
assert.ok(a.world.messages.length > 0, 'agents should exchange observations and needs');
assert.ok(a.world.proposals.length === a.tick * a.agents.length, 'every agent should submit one proposal per tick');
assert.ok(a.world.proposals.every(p => a.agents.some(agent => agent.id === p.agentId)), 'every proposal must have provenance');
assert.ok(a.world.proposals.some(p => !p.accepted), 'conflicting proposals should be rejected deterministically');
assert.ok(a.world.proposals.every(p => ['selected-by-priority-and-stable-id', 'conflict-lost', 'invalid-world-reference'].includes(p.reason)), 'every proposal must have a resolution reason');
assert.ok(a.world.messages.every(m => a.agents.some(agent => agent.id === m.from) && a.agents.some(agent => agent.id === m.to)), 'messages must have valid sender and recipient');
assert.ok(a.agents.some(agent => agent.inbox.length > 0), 'agents should receive peer signals');
assert.ok(a.agents.every(agent => agent.energy >= 0 && agent.energy <= 16), 'agent energy must remain bounded');
console.log(JSON.stringify({
  result: 'PASS', prototype: 'autonomous-genesis-sandbox', seed: a.seed, ticks: a.tick,
  agents: a.agents.length, terrain: a.world.terrain.length, biomes: a.world.biomes.length,
  organisms: a.world.organisms.length, decisions: a.world.events.length, proposals: a.world.proposals.length,
  acceptedProposals: a.world.proposals.filter(proposal => proposal.accepted).length,
  rejectedProposals: a.world.proposals.filter(proposal => !proposal.accepted).length,
  goalChanges: a.agents.reduce((sum, agent) => sum + agent.goalChanges, 0),
  messages: a.world.messages.length,
  agentsReceivingMessages: a.agents.filter(agent => agent.inbox.length > 0).length,
  ecologicalFeedbackTicks: a.world.ecology.length,
  checkpointRestore: 'PASS', midRunReplay: 'PASS',
  deterministicReplay: true, persistence: 'disabled', network: 'disabled', productionChanges: 'none',
}, null, 2));
