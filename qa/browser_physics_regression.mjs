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

await page.route(`${new URL(url).origin}/**`, async route => {
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
  // Separate server hydration from the client diagnostics hook so a missing hook
  // fails quickly with useful runtime evidence instead of a generic 125s timeout.
  await page.waitForFunction(() => window.__AION_SYNCED === true || !!window.__AION_SYNC_ERROR, null, { timeout: 125000, polling: 500 });
  const startup = await page.evaluate(() => ({
    synced: window.__AION_SYNCED === true,
    hasServerState: !!window.__AION_SERVER_STATE,
    hasQaHook: !!window.__AION_QA && typeof window.__AION_QA.snapshot === "function",
    syncError: window.__AION_SYNC_ERROR,
    readyState: document.readyState,
    title: document.title,
    canvasCount: document.querySelectorAll("canvas").length
  }));
  if (startup.syncError) throw new Error(`AION server hydration failed: ${startup.syncError}`);
  if (!startup.hasQaHook) throw new Error(`AION QA diagnostics hook missing after hydration: ${JSON.stringify(startup)}; browserErrors=${JSON.stringify(errors)}`);
  const before = await page.evaluate(() => window.__AION_QA.snapshot());
  fs.mkdirSync("artifacts", { recursive: true });
  await page.screenshot({ path: "artifacts/04-physics-before.png" });

  // Verify actual camera input paths, including a two-pointer pinch gesture.
  const cameraStart = before.cameraDistance;
  await page.locator("canvas").hover();
  await page.mouse.wheel(0, 100);
  await page.waitForTimeout(100);
  const afterWheel = await page.evaluate(() => window.__AION_QA.snapshot().cameraDistance);
  const wheelZoomWorks = Number.isFinite(afterWheel) && afterWheel > cameraStart;

  const pinchStart = await page.evaluate(() => window.__AION_QA.snapshot().cameraDistance);
  await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    // Synthetic pointers do not own browser pointer capture; neutralize capture only for this test.
    canvas.setPointerCapture = () => {};
    canvas.releasePointerCapture = () => {};
    const fire = (target, type, pointerId, x, y) => target.dispatchEvent(new PointerEvent(type, {
      pointerId, pointerType: "touch", clientX: x, clientY: y, bubbles: true
    }));
    fire(canvas, "pointerdown", 101, 100, 100);
    fire(canvas, "pointerdown", 102, 200, 100);
    fire(window, "pointermove", 102, 240, 100);
    fire(canvas, "pointerup", 102, 240, 100);
    fire(canvas, "pointerup", 101, 100, 100);
  });
  await page.waitForTimeout(100);
  const afterPinch = await page.evaluate(() => window.__AION_QA.snapshot().cameraDistance);
  const pinchZoomWorks = Number.isFinite(afterPinch) && afterPinch < pinchStart;
  await page.waitForTimeout(10000);
  const after = await page.evaluate(() => window.__AION_QA.snapshot());
  const dist = (a, b) => Math.hypot(a.x-b.x, a.y-b.y, a.z-b.z);
  const old = new Map(before.agents.map(a => [a.id, a]));
  const moved = after.agents.filter(a => old.has(a.id) && dist(a, old.get(a.id)) > 0.15).length;
  const allBodies = [...after.agents, ...after.animals];
  const finite = allBodies.every(a => [a.x,a.y,a.z,a.floorY,a.height,a.vx,a.vy,a.vz].every(Number.isFinite));
  const terrainSupport = allBodies.map(a => ({ id: a.id, gap: a.y - a.floorY })).filter(a => Math.abs(a.gap) > 0.20);
  const groundedOnTerrain = terrainSupport.length === 0;
  const maxHorizontalSpeed = Math.max(0, ...allBodies.map(a => Math.hypot(a.vx,a.vz)));
  const speedBounded = maxHorizontalSpeed <= 2.21;
  const displacementRows = after.agents.filter(a => old.has(a.id)).map(a => ({ id: a.id, from: old.get(a.id), to: a, distance: dist(a, old.get(a.id)) }));
  const maxDisplacementRow = displacementRows.reduce((best, row) => !best || row.distance > best.distance ? row : best, null);
  const maxDisplacement = maxDisplacementRow?.distance || 0;
  const noTeleport = maxDisplacement <= 2.2 * 10 + 1.0;
  const overlaps = [];
  for (let i = 0; i < allBodies.length; i++) for (let j = i + 1; j < allBodies.length; j++) {
    const a = allBodies[i], b = allBodies[j];
    const d = Math.hypot(a.x-b.x, a.z-b.z);
    const verticalOverlap = a.y < b.y + (b.height||1.0) && b.y < a.y + (a.height||1.0);
    if (verticalOverlap && d < (a.radius||.38) + (b.radius||.38) - .12) overlaps.push({type:"body-body",a:a.id,b:b.id,penetration:Number(((a.radius||.38)+(b.radius||.38)-d).toFixed(3))});
  }
  for (const a of allBodies) for (const s of after.colliders) {
    const d = Math.hypot(a.x-s.x, a.z-s.z);
    const verticalOverlap = a.y < s.y + (s.height||1.0) && s.y < a.y + (a.height||1.0);
    if (verticalOverlap && d < (a.radius||.38) + (s.radius||.5) - .12) overlaps.push({type:"body-collider",body:a.id,collider:s.id,penetration:Number(((a.radius||.38)+(s.radius||.5)-d).toFixed(3))});
  }
  const severeOverlapCount = overlaps.length;
  const sameWorld = before.worldVersion === after.worldVersion;
  const noUnexpectedMutation = blockedMutations.every(x => x.path === "/physics/colliders");
  const result = {
    ok: before.serverConnected && after.serverConnected && after.agents.length > 0 &&
      moved > 0 && finite && groundedOnTerrain && speedBounded && noTeleport && severeOverlapCount === 0 && sameWorld && noUnexpectedMutation && wheelZoomWorks && pinchZoomWorks && errors.length === 0,
    checks: { hydrated: !!after.serverConnected, residentCount: after.agents.length, residentsMoved: moved,
      finiteTransforms: finite, groundedOnTerrain, terrainSupportIssues: terrainSupport, maxHorizontalSpeed: Number(maxHorizontalSpeed.toFixed(4)),
      speedBounded, maxDisplacement10s: Number(maxDisplacement.toFixed(3)), noTeleport,
      maxDisplacementAgent: maxDisplacementRow ? { id: maxDisplacementRow.id, distance: Number(maxDisplacementRow.distance.toFixed(3)), from: { x: maxDisplacementRow.from.x, y: maxDisplacementRow.from.y, z: maxDisplacementRow.from.z, vx: maxDisplacementRow.from.vx, vy: maxDisplacementRow.from.vy, vz: maxDisplacementRow.from.vz }, to: { x: maxDisplacementRow.to.x, y: maxDisplacementRow.to.y, z: maxDisplacementRow.to.z, vx: maxDisplacementRow.to.vx, vy: maxDisplacementRow.to.vy, vz: maxDisplacementRow.to.vz } } : null,
      severeOverlapCount, overlaps: overlaps.slice(0,30), sameWorld, camera: { start: cameraStart, afterWheel, wheelZoomWorks, pinchStart, afterPinch, pinchZoomWorks }, blockedMutationAttempts: blockedMutations, noUnexpectedMutation, browserErrors: errors },
    before: { worldVersion: before.worldVersion, residents: before.agents.length },
    after: { worldVersion: after.worldVersion, residents: after.agents.length }
  };
  fs.writeFileSync("artifacts/aion-physics-regression.json", JSON.stringify(result, null, 2));
  await page.screenshot({ path: "artifacts/05-physics-after.png" });
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.ok ? 0 : 1;
} finally {
  await browser.close();
}
