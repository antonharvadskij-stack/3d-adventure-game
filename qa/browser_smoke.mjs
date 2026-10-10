import { chromium } from "playwright";
import fs from "node:fs";

const url = process.env.AION_CLIENT_URL;
if (!url) throw new Error("AION_CLIENT_URL is required");
fs.mkdirSync("artifacts", { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
const failedRequests = [];
page.on("pageerror", e => errors.push("pageerror: " + e.message));
page.on("requestfailed", r => failedRequests.push(r.url() + " :: " + (r.failure()?.errorText || "unknown")));
page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()); });

const inspect = async name => {
  const dom = await page.evaluate(() => {
    const rect = selector => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height), right: Math.round(r.right), bottom: Math.round(r.bottom) };
    };
    return {
      title: document.title,
      viewport: { width: innerWidth, height: innerHeight },
      canvas: rect("canvas"),
      panel: rect("#panel"),
      epoch: rect("#epoch"),
      reset: rect("#resetBtn"),
      log: rect("#log"),
      god: rect("#god"),
      cameraHint: rect("#cam"),
      calendar: document.querySelector("#worldCalendar")?.innerText || "",
      elapsed: document.querySelector("#worldElapsed")?.innerText || "",
      epochText: document.querySelector("#ep")?.innerText || "",
      panelOpen: document.querySelector("#panel")?.classList.contains("open") || false,
      statsVisible: !!document.querySelector("#state") && getComputedStyle(document.querySelector("#state")).display !== "none",
      stateText: document.querySelector("#state")?.innerText || "",
      connectionLogCount: [...document.querySelectorAll("#log .event")].filter(el => el.textContent.includes("AION подключён к постоянному серверному миру")).length,
      synced: window.__AION_SYNCED === true,
      world: window.__AION_SERVER_STATE ? {
        worldVersion: Number(window.__AION_SERVER_STATE.worldVersion || 0),
        population: Array.isArray(window.__AION_SERVER_STATE.population) ? window.__AION_SERVER_STATE.population.length : -1,
        firstAgentPosition: Array.isArray(window.__AION_SERVER_STATE.population) && window.__AION_SERVER_STATE.population[0] ? {
          x: Number(window.__AION_SERVER_STATE.population[0].x || 0),
          y: Number(window.__AION_SERVER_STATE.population[0].y || 0),
          z: Number(window.__AION_SERVER_STATE.population[0].z || 0)
        } : null,
        epoch: window.__AION_SERVER_STATE.epoch,
        worldAge: Number(window.__AION_SERVER_STATE.worldAge || 0),
      } : null,
      webgl: !!document.querySelector("canvas")?.getContext("webgl2"),
      overlaps: (() => {
        const rects = {};
        for (const key of ["panel", "epoch", "resetBtn", "log", "god", "cam"]) {
          const el = document.querySelector(key === "resetBtn" ? "#resetBtn" : key === "cam" ? "#cam" : "#" + key);
          if (el) { const r = el.getBoundingClientRect(); rects[key] = {x:r.x,y:r.y,right:r.right,bottom:r.bottom}; }
        }
        const overlap = (a,b) => !!rects[a] && !!rects[b] && rects[a].x < rects[b].right && rects[a].right > rects[b].x && rects[a].y < rects[b].bottom && rects[a].bottom > rects[b].y;
        return {panel_epoch:overlap("panel","epoch"),panel_reset:overlap("panel","resetBtn"),log_god:overlap("log","god"),cam_god:overlap("cam","god")};
      })(),
    };
  });
  await page.screenshot({ path: `artifacts/${name}.png`, fullPage: true });
  return dom;
};

try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() =>
    window.__AION_SYNCED === true &&
    !!window.__AION_SERVER_STATE &&
    Number.isFinite(Number(window.__AION_SERVER_STATE.worldVersion)),
    undefined, { timeout: 90000, polling: 500 }
  );
  await page.waitForTimeout(2500);
  const initial = await inspect("01-desktop-initial");

  if (!initial.canvas || initial.canvas.width < 300 || initial.canvas.height < 250) throw new Error("3D canvas missing or too small");
  if (!initial.webgl) throw new Error("WebGL2 context unavailable");
  if (!initial.world || initial.world.worldVersion < 1) throw new Error("Server world did not hydrate");
  if (!initial.calendar.includes("Год") || !initial.calendar.includes("День")) throw new Error("Earth-origin calendar missing");
  if (!initial.elapsed.includes("С начала рождения Земли")) throw new Error("Elapsed-from-Earth-origin label missing");

  // UI interaction only: never click the destructive Big Bang/reset action.
  await page.locator("#hudToggle").click();
  await page.waitForFunction(() => document.querySelector("#panel")?.classList.contains("open"));
  const hud = await inspect("02-desktop-hud-open");
  if (!hud.statsVisible) throw new Error("HUD toggle did not reveal diagnostics");
  if (!hud.stateText.includes("Жители мира:")) throw new Error("HUD population does not report the server world count");
  if (hud.connectionLogCount > 1) throw new Error("Connection log is being duplicated on polling");

  // Exercise camera input without changing server state.
  const canvas = page.locator("canvas");
  const beforeBox = await canvas.boundingBox();
  await page.mouse.move(beforeBox.x + beforeBox.width * 0.5, beforeBox.y + beforeBox.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(beforeBox.x + beforeBox.width * 0.62, beforeBox.y + beforeBox.height * 0.56, { steps: 5 });
  await page.mouse.up();
  await page.mouse.wheel(0, -120);
  await page.waitForTimeout(500);
  await inspect("03-desktop-camera-input");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const mobile = await inspect("04-mobile-layout");
  if (Object.values(mobile.overlaps || {}).some(Boolean)) throw new Error("Mobile HUD panels overlap: " + JSON.stringify(mobile.overlaps));
  const startPosition = initial.world?.firstAgentPosition;
  if (startPosition) {
    await page.waitForFunction(start => {
      const a = window.__AION_SERVER_STATE?.population?.[0];
      if (!a) return false;
      const dx = Number(a.x || 0) - start.x;
      const dz = Number(a.z || 0) - start.z;
      return Math.hypot(dx, dz) > 0.2;
    }, startPosition, { timeout: 20000, polling: 500 });
  }
  const required = ["canvas", "panel", "epoch", "reset", "log", "god"];
  for (const key of required) {
    const r = key === "reset" ? mobile.reset : mobile[key];
    if (!r) throw new Error("Mobile layout missing element: " + key);
    if (r.x < -2 || r.y < -2 || r.right > mobile.viewport.width + 2 || r.bottom > mobile.viewport.height + 2) {
      throw new Error("Mobile layout element out of viewport: " + key + " " + JSON.stringify(r));
    }
  }

  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() =>
    window.__AION_SYNCED === true && !!window.__AION_SERVER_STATE &&
    Number.isFinite(Number(window.__AION_SERVER_STATE.worldVersion)),
    undefined, { timeout: 90000, polling: 500 }
  );
  await page.waitForTimeout(500);
  const afterReload = await inspect("05-mobile-after-reload");
  if (!afterReload.world || afterReload.world.worldVersion < 1) throw new Error("World state did not restore after reload");

  const seriousRequestFailures = failedRequests.filter(x => !x.includes("ERR_ABORTED"));
  const result = {
    ok: errors.length === 0 && seriousRequestFailures.length === 0,
    checks: {
      webgl_canvas: !!initial.webgl && !!initial.canvas,
      server_world_hydrated: !!initial.world,
      earth_origin_calendar: initial.calendar.includes("Год") && initial.calendar.includes("День") && initial.elapsed.includes("С начала рождения Земли"),
      hud_toggle: hud.panelOpen && hud.statsVisible,
      camera_input: true,
      mobile_layout_in_viewport: true,
      world_restores_after_reload: !!afterReload.world,
      no_page_or_console_errors: errors.length === 0,
      no_failed_network_requests: seriousRequestFailures.length === 0
    },
    snapshots: { initial, hud, mobile, afterReload },
    errors,
    failedRequests: seriousRequestFailures
  };
  fs.writeFileSync("artifacts/aion-lifecycle-report.json", JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 1;
} catch (e) {
  const failure = {
    ok: false,
    error: e?.stack || String(e),
    errors,
    failedRequests
  };
  fs.writeFileSync("artifacts/aion-lifecycle-report.json", JSON.stringify(failure, null, 2));
  console.error(JSON.stringify(failure, null, 2));
  process.exitCode = 1;
} finally {
  await browser.close();
}
