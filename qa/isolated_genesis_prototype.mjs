#!/usr/bin/env node
/**
 * Isolated AION Genesis physics prototype.
 * Dependency-free, deterministic, no network, no persistence, no production imports.
 * Run: node qa/isolated_genesis_prototype.mjs
 */
import assert from "node:assert/strict";

const DT = 1 / 60;
const DURATION_SECONDS = 120;
const STEPS = Math.round(DURATION_SECONDS / DT);
const MAX_SPEED = 1.15;
const POSITION_EPSILON = 1e-4;
const MAX_STEP_DISPLACEMENT = MAX_SPEED * DT + POSITION_EPSILON;

function rng(seed = 0xA10A) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function createWorld(seed = 0xA10A) {
  const random = rng(seed);
  return {
    time: 0,
    tick: 0,
    terrain: { kind: "flat-baseline", height: () => 0 },
    agents: Array.from({ length: 8 }, (_, i) => ({
      id: `genesis-${i + 1}`,
      x: (random() - 0.5) * 20,
      z: (random() - 0.5) * 20,
      vx: 0,
      vz: 0,
      targetX: (random() - 0.5) * 40,
      targetZ: (random() - 0.5) * 40,
      maxSpeed: MAX_SPEED,
    })),
    telemetry: [],
  };
}

function stepAgent(agent, dt) {
  let dx = agent.targetX - agent.x;
  let dz = agent.targetZ - agent.z;
  let distance = Math.hypot(dx, dz);
  if (distance < 0.5) {
    // Deterministic target update based on identity and simulation tick is handled by caller.
    agent.vx = 0;
    agent.vz = 0;
    return;
  }
  const speed = Math.min(agent.maxSpeed, distance / dt);
  agent.vx = (dx / distance) * speed;
  agent.vz = (dz / distance) * speed;
  agent.x += agent.vx * dt;
  agent.z += agent.vz * dt;
}

function inspectStep(before, after, tick, dt) {
  const distance = Math.hypot(after.x - before.x, after.z - before.z);
  const allowed = after.maxSpeed * dt + POSITION_EPSILON;
  if (![after.x, after.z, after.vx, after.vz, distance].every(Number.isFinite)) {
    return { tick, agentId: after.id, reason: "non-finite-transform", distance };
  }
  if (distance > allowed) {
    return {
      tick,
      agentId: after.id,
      reason: "discontinuity",
      distance: Number(distance.toFixed(6)),
      allowed: Number(allowed.toFixed(6)),
      from: { x: before.x, z: before.z, vx: before.vx, vz: before.vz },
      to: { x: after.x, z: after.z, vx: after.vx, vz: after.vz },
    };
  }
  const horizontalSpeed = Math.hypot(after.vx, after.vz);
  if (horizontalSpeed > after.maxSpeed + POSITION_EPSILON) {
    return { tick, agentId: after.id, reason: "speed-bound-exceeded", horizontalSpeed };
  }
  return null;
}

function runSimulation({ seed = 0xA10A, injectDiscontinuity = false } = {}) {
  const world = createWorld(seed);
  const faults = [];
  let maxObservedSpeed = 0;
  let maxObservedStep = 0;

  for (let tick = 1; tick <= STEPS; tick++) {
    for (const agent of world.agents) {
      const before = { ...agent };
      stepAgent(agent, DT);

      // Controlled fault injection validates that the detector catches an abrupt jump.
      if (injectDiscontinuity && tick === 600 && agent.id === "genesis-3") {
        agent.x += 50;
      }

      const fault = inspectStep(before, agent, tick, DT);
      if (fault) faults.push(fault);
      maxObservedStep = Math.max(maxObservedStep, Math.hypot(agent.x - before.x, agent.z - before.z));
      maxObservedSpeed = Math.max(maxObservedSpeed, Math.hypot(agent.vx, agent.vz));
    }
    world.tick = tick;
    world.time = tick * DT;
    if (tick % 600 === 0) {
      world.telemetry.push({
        tick,
        timeSeconds: Number(world.time.toFixed(3)),
        agentCount: world.agents.length,
        maxObservedSpeed: Number(maxObservedSpeed.toFixed(6)),
        maxObservedStep: Number(maxObservedStep.toFixed(6)),
        faults: faults.length,
      });
    }
  }

  return {
    ok: faults.length === 0,
    seed,
    durationSeconds: DURATION_SECONDS,
    fixedStepSeconds: DT,
    ticks: STEPS,
    agentCount: world.agents.length,
    maxSpeedLimit: MAX_SPEED,
    maxObservedSpeed: Number(maxObservedSpeed.toFixed(6)),
    maxObservedStep: Number(maxObservedStep.toFixed(6)),
    faults,
    telemetry: world.telemetry,
    persistence: "disabled",
    network: "disabled",
    productionImports: "none",
  };
}

const baseline = runSimulation();
assert.equal(baseline.ok, true, "baseline Genesis simulation must not produce discontinuities");
assert.equal(baseline.faults.length, 0);
assert.ok(baseline.maxObservedSpeed <= MAX_SPEED + POSITION_EPSILON);

const injected = runSimulation({ injectDiscontinuity: true });
assert.equal(injected.ok, false, "injected jump must fail the discontinuity detector");
assert.ok(injected.faults.some(f => f.reason === "discontinuity" && f.agentId === "genesis-3"));

console.log(JSON.stringify({
  result: "PASS",
  prototype: "isolated-genesis-physics",
  baseline: { ok: baseline.ok, ticks: baseline.ticks, durationSeconds: baseline.durationSeconds, agentCount: baseline.agentCount, maxObservedSpeed: baseline.maxObservedSpeed, faults: baseline.faults.length },
  faultInjection: { detected: !injected.ok, detectedFaults: injected.faults.length, firstFault: injected.faults[0] },
  telemetry: baseline.telemetry,
  safety: { persistence: "disabled", network: "disabled", productionChanges: "none", bigBang: "not run" },
}, null, 2));
