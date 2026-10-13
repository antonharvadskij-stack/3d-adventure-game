import { chromium } from "playwright";
import fs from "node:fs";

const url = process.env.AION_CLIENT_URL;
if (!url) throw new Error("AION_CLIENT_URL is required");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
const blockedMutations = [];
page.on("pageerror", e => errors.push(e.message));
page.on("console", m => { if (m.type() === "error" && !/ERR_BLOCKED_BY_CLIENT|blocked_by_client/i.test(m.text())) errors.push(m.text()); });

await page.route("https://aion-server-b80c.onrender.com/**", async route => {
  const request = route.request();
  const method = request.method().toUpperCase();
  const path = new URL(request.url()).pathname;
  if (method === "GET" && path === "/") {
    await route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: fs.readFileSync("../index.html", "utf8") });
    return;
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    blockedMutations.push({ method, path });
    await route.abort("blockedbyclient");
    return;
  }
  await route.continue();
});

try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => window.__AION_SYNCED === true && !!window.__AION_QA, null, { timeout: 125000, polling: 500 });
  const before = await page.evaluate(() => window.__AION_QA.snapshot());
  await page.waitForTimeout(10000);
  const after = await page.evaluate(() => window.__AION_QA.snapshot());
  const dist = (a, b) => Math.hypot(a.x-b.x, a.y-b.y, a.z-b.z);
  const old = new Map(before.agents.map(a => [a.id, a]));
  const moved = after.agents.filter(a => old.has(a.id) && dist(a, old.get(a.id)) > 0.15).length;
  const allBodies = [...after.agents, ...after.animals];
  const finite = allBodies.every(a => [a.x,a.y,a.z,a.vx,a.vy,a.vz].every(Number.isFinite));
  const maxHorizontalSpeed = Math.max(0, ...allBodies.map(a => Math.hypot(a.vx,a.vz)));
  const speedBounded = maxHorizontalSpeed <= 2.21;
  const sameWorld = before.worldVersion === after.worldVersion;
  const noUnexpectedMutation = blockedMutations.every(x => x.path === "/physics/colliders");
  const result = {
    ok: before.serverConnected && after.serverConnected && after.agents.length > 0 &&
      moved > 0 && finite && speedBounded && sameWorld && noUnexpectedMutation && errors.length === 0,
    checks: { hydrated: !!after.serverConnected, residentCount: after.agents.length, residentsMoved: moved,
      finiteTransforms: finite, maxHorizontalSpeed: Number(maxHorizontalSpeed.toFixed(4)),
      speedBounded, sameWorld, blockedMutationAttempts: blockedMutations, noUnexpectedMutation, browserErrors: errors },
    before: { worldVersion: before.worldVersion, residents: before.agents.length },
    after: { worldVersion: after.worldVersion, residents: after.agents.length }
  };
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.ok ? 0 : 1;
} finally {
  await browser.close();
}
