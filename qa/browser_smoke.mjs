import { chromium } from "playwright";
import fs from "node:fs";

const url = process.env.AION_CLIENT_URL;
if (!url) throw new Error("AION_CLIENT_URL is required");

fs.mkdirSync("artifacts", { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", error => errors.push("pageerror: " + error.message));
page.on("console", message => {
  if (message.type() === "error") errors.push("console: " + message.text());
});
page.on("requestfailed", request => {
  const failure = String(request.failure()?.errorText || "").toLowerCase();
  if (!failure.includes("blocked_by_client") && !failure.includes("blockedbyclient")) {
    errors.push("requestfailed: " + request.method() + " " + request.url() + " " + failure);
  }
});
page.on("response", response => {
  if (response.status() >= 500) errors.push("HTTP " + response.status() + ": " + response.url());
});
const blockedMutations = [];
const destructiveAttempts = [];
await page.route("https://aion-server-b80c.onrender.com/**", async route => {
  const request = route.request();
  const method = request.method().toUpperCase();
  const path = new URL(request.url()).pathname;
  // Serve the checked-out branch client at the production origin so API calls remain same-origin.
  // This validates the candidate commit without deploying it to production.
  if (method === "GET" && path === "/") {
    await route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: fs.readFileSync("../index.html", "utf8") });
    return;
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const entry = { url: request.url(), method };
    blockedMutations.push(entry);
    if (path === "/world/reset" || path === "/debug/persistence-test" || path === "/world/tick") {
      destructiveAttempts.push(entry);
    }
    await route.abort("blockedbyclient");
    return;
  }
  await route.continue();
});
const waitForServerHydration = async () => page.waitForFunction(
  () => window.__AION_SYNCED === true &&
    !!window.__AION_SERVER_STATE &&
    Number.isFinite(Number(window.__AION_SERVER_STATE.worldVersion)),
  undefined,
  { timeout: 120000, polling: 500 }
);
const read = async () => ({
  state: await page.locator("#state").innerText().catch(() => ""),
  time: await page.locator("#worldTime").innerText().catch(() => ""),
  year: await page.locator("#worldElapsed").innerText().catch(() => ""),
  epoch: await page.locator("#ep").innerText().catch(() => ""),
  log: await page.locator("#log").innerText().catch(() => "")
});
const apiRead = async () => page.evaluate(() =>
  window.__AION_SERVER_STATE ? JSON.parse(JSON.stringify(window.__AION_SERVER_STATE)) : null
);
const snapshots = [];

await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
await waitForServerHydration();
snapshots.push({ name: "initial", data: await read(), api: await apiRead() });
await page.screenshot({ path: "artifacts/01-initial.png" });

// Read-only lifecycle check: the test harness never clicks reset or manually triggers a world tick. The app may register runtime colliders on load.
await page.waitForTimeout(15000);
await waitForServerHydration();
snapshots.push({ name: "after_observation", data: await read(), api: await apiRead() });
await page.screenshot({ path: "artifacts/02-after-observation.png" });

await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
await waitForServerHydration();
await page.waitForTimeout(1000);
snapshots.push({ name: "after_reload", data: await read(), api: await apiRead() });
await page.screenshot({ path: "artifacts/03-after-reload.png" });

const initial = snapshots[0].api;
const observed = snapshots[1].api;
const reloaded = snapshots[2].api;
const noBrowserErrors = errors.filter(e => !e.includes("502") && !e.includes("blockedbyclient")).length === 0;
const worldRemainsValid =
  Number.isFinite(Number(initial.worldAge)) &&
  Number.isFinite(Number(observed.worldAge)) &&
  Number.isFinite(Number(reloaded.worldAge)) &&
  Number(observed.worldAge) >= Number(initial.worldAge) &&
  Number(reloaded.worldAge) >= Number(observed.worldAge) &&
  Number(reloaded.cycle) >= Number(observed.cycle) &&
  Number(reloaded.worldVersion) >= Number(observed.worldVersion);
const result = {
  ok: noBrowserErrors && worldRemainsValid && destructiveAttempts.length === 0,
  safety: { all_non_read_only_api_requests_blocked_before_network: true, blockedMutations, destructiveAttempts },
  checks: {
    server_hydration: true,
    no_browser_errors: noBrowserErrors,
    no_destructive_mutation_attempts: destructiveAttempts.length === 0,
    world_state_monotonic: worldRemainsValid,
    transient_server_502: errors.some(e => e.includes("502"))
  },
  snapshots,
  errors
};
fs.writeFileSync("artifacts/aion-lifecycle-report.json", JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
process.exitCode = result.ok ? 0 : 1;
