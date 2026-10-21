import test from "node:test";
import assert from "node:assert/strict";
import { createGenesis, proposeWorldEvent, applyProposal, godAiStep, tickGenesis, LIMITS } from "./void-sim.mjs";

test("starts in true VOID without world entities", () => {
  const s = createGenesis(7);
  assert.equal(s.phase, "VOID");
  assert.deepEqual(s.terrain, []);
  assert.equal(s.climate, null);
  assert.deepEqual(s.organisms, []);
  assert.deepEqual(s.agents, []);
});

test("God AI proposes but cannot bypass explicit validation/application", () => {
  const s = createGenesis(7);
  const p = godAiStep(s);
  assert.equal(s.terrain.length, 0);
  assert.equal(p.status, "PENDING");
  assert.equal(applyProposal(s, p.id).status, "ACCEPTED");
  assert.equal(s.terrain.length, 1);
});

test("rejects unsafe climate and invalid coordinates", () => {
  const s = createGenesis(1);
  const badClimate = proposeWorldEvent(s, { type: "SET_CLIMATE", temperature: 1000 });
  assert.equal(applyProposal(s, badClimate.id).status, "REJECTED");
  const badAgent = proposeWorldEvent(s, { type: "SPAWN_AGENT", x: Infinity, z: 0 });
  assert.equal(applyProposal(s, badAgent.id).status, "REJECTED");
  assert.equal(s.agents.length, 0);
});

test("agents retain stable IDs and bounded movement", () => {
  const s = createGenesis(11);
  for (let i = 0; i < 4; i++) { const p = godAiStep(s); applyProposal(s, p.id); }
  const id = s.agents[0].id;
  const before = { ...s.agents[0] };
  tickGenesis(s);
  assert.equal(s.agents[0].id, id);
  assert.ok(Math.hypot(s.agents[0].x - before.x, s.agents[0].z - before.z) <= LIMITS.maxStep + 1e-9);
});

test("refuses to tick from empty VOID", () => {
  assert.throws(() => tickGenesis(createGenesis(1)), /empty VOID/);
});
