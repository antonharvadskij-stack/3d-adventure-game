import { chromium } from "playwright";
import fs from "node:fs";

const url = process.env.AION_CLIENT_URL;
if (!url) throw new Error("AION_CLIENT_URL is required");
const testOrigin = new URL(url).origin;
const productionOrigin = "https://aion-server-b80c.onrender.com";
const qaUrl = new URL(url);
qaUrl.searchParams.set("server", testOrigin);

fs.mkdirSync("artifacts", { recursive: true });

// Independent, read-only server probes run before Chromium. They distinguish
// server/API availability from client hydration failures without changing state.
const probeReadOnlyEndpoint = async path => {
  const started = Date.now();
  try {
    const response = await fetch(testOrigin + path, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });
    const result = {
      path,
      status: response.status,
      ok: response.ok,
      duration_ms: Date.now() - started,
      content_type: response.headers.get("content-type")
    };
    if (path === "/world" && response.ok) {
      try {
        const payload = await response.json();
        result.json_object = !!payload && typeof payload === "object" && !Array.isArray(payload);
        result.top_level_keys = result.json_object ? Object.keys(payload).slice(0, 40) : [];
        result.world_version_finite = Number.isFinite(Number(payload?.worldVersion));
      } catch (error) {
        result.body_parse_error = String(error?.name || "Error");
      }
    }
    return result;
  } catch (error) {
    return {
      path,
      ok: false,
      duration_ms: Date.now() - started,
      error_name: String(error?.name || "Error"),
      error_message: String(error?.message || error).slice(0, 240)
    };
  }
};
const serverProbes = [];
serverProbes.push(await probeReadOnlyEndpoint("/health"));
serverProbes.push(await probeReadOnlyEndpoint("/world"));

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
const blockedMutations = [];
const destructiveAttempts = [];
const crossOriginRequests = [];
const forbiddenProductionRequests = [];

page.on("pageerror", error => errors.push("pageerror: " + error.message));
page.on("console", message => {
  if (message.type() !== "error") return;
  const text = message.text();
  // Chromium emits console errors for requests intentionally aborted by the QA safety guard.
  if (/ERR_BLOCKED_BY_CLIENT|blocked_by_client|blockedbyclient/i.test(text)) return;
  errors.push("console: " + text);
});
page.on("requestfailed", request => {
  const failure = String(request.failure()?.errorText || "").toLowerCase();
  // Chromium reports fetches cancelled by page.reload()/navigation as net::ERR_ABORTED.
  // This is expected during the read-only lifecycle test, not a browser/server failure.
  if (failure.includes("err_aborted") || failure.includes("aborted_by_navigation")) return;
  if (!failure.includes("blocked_by_client") && !failure.includes("blockedbyclient")) {
    errors.push("requestfailed: " + request.method() + " " + request.url() + " " + failure);
  }
});
page.on("response", response => {
  if (response.status() >= 500) errors.push("HTTP " + response.status() + ": " + response.url());
});

await page.route("**/*", async route => {
  const request = route.request();
  const method = request.method().toUpperCase();
  const requestUrl = new URL(request.url());
  const path = requestUrl.pathname;

  // Permit only the pinned Three.js CDN modules required by index.html.
  // Three.js imports three.core.js from three.module.js; no other CDN paths are allowed.
  // All other cross-origin traffic remains blocked; production is never allowlisted.
  const allowedThreeJsAssets = new Set([
    "/npm/three@0.180.0/build/three.module.js",
    "/npm/three@0.180.0/build/three.core.js"
  ]);
  const allowedStaticCdnRequest =
    requestUrl.origin === "https://cdn.jsdelivr.net" &&
    method === "GET" &&
    allowedThreeJsAssets.has(requestUrl.pathname);
  if (requestUrl.origin !== testOrigin && !allowedStaticCdnRequest) {
    const entry = { url: request.url(), method, origin: requestUrl.origin };
    crossOriginRequests.push(entry);
    if (requestUrl.origin === productionOrigin) forbiddenProductionRequests.push(entry);
    errors.push("blocked cross-origin request: " + method + " " + request.url());
    await route.abort("blockedbyclient");
    return;
  }

  // Serve the checked-out branch client at the isolated test origin.
  // The query parameter explicitly selects the test API in index.html.
  if (method === "GET" && path === "/") {
    await route.fulfill({
      status: 200,
      contentType: "text/html; charset=utf-8",
      body: fs.readFileSync("../index.html", "utf8")
    });
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

const waitForServerHydration = async () => {
  try {
    await page.waitForFunction(
      () => window.__AION_SYNCED === true &&
        !!window.__AION_SERVER_STATE &&
        Number.isFinite(Number(window.__AION_SERVER_STATE.worldVersion)),
      undefined,
      { timeout: 125000, polling: 500 }
    );
    return true;
  } catch (error) {
    errors.push("server hydration timeout: " + error.message);
    return false;
  }
};

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
const hydration = [];

await page.goto(qaUrl.toString(), { waitUntil: "domcontentloaded", timeout: 60000 });
hydration.push(await waitForServerHydration());
snapshots.push({ name: "initial", data: await read(), api: await apiRead() });
await page.screenshot({ path: "artifacts/01-initial.png" });

// Continue lifecycle checks only when initial hydration succeeds. A failed startup still produces a useful diagnostic artifact.
if (hydration[0]) {
  // Read-only lifecycle check. All non-read-only API requests are intercepted before network access.
  await page.waitForTimeout(15000);
  hydration.push(await waitForServerHydration());
  snapshots.push({ name: "after_observation", data: await read(), api: await apiRead() });
  await page.screenshot({ path: "artifacts/02-after-observation.png" });

  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  hydration.push(await waitForServerHydration());
  await page.waitForTimeout(1000);
  snapshots.push({ name: "after_reload", data: await read(), api: await apiRead() });
  await page.screenshot({ path: "artifacts/03-after-reload.png" });
}

const initial = snapshots[0]?.api;
const observed = snapshots[1]?.api;
const reloaded = snapshots[2]?.api;
const noBrowserErrors = errors.length === 0;
const worldRemainsValid = !!initial && !!observed && !!reloaded &&
  Number.isFinite(Number(initial.worldAge)) &&
  Number.isFinite(Number(observed.worldAge)) &&
  Number.isFinite(Number(reloaded.worldAge)) &&
  Number(observed.worldAge) >= Number(initial.worldAge) &&
  Number(reloaded.worldAge) >= Number(observed.worldAge) &&
  Number(reloaded.cycle) >= Number(observed.cycle) &&
  Number(reloaded.worldVersion) >= Number(observed.worldVersion);
const result = {
  candidate_sha: process.env.AION_CANDIDATE_SHA || null,
  server_probes: serverProbes,
  test_target: url,
  browser_url: qaUrl.toString(),
  ok: hydration.length === 3 && hydration.every(Boolean) &&
    noBrowserErrors && worldRemainsValid && destructiveAttempts.length === 0 &&
    crossOriginRequests.length === 0 && forbiddenProductionRequests.length === 0,
  safety: {
    all_non_read_only_api_requests_blocked_before_network: true,
    cross_origin_requests_blocked_before_network: true,
    blockedMutations, destructiveAttempts, crossOriginRequests, forbiddenProductionRequests
  },
  checks: {
    server_hydration: hydration.length === 3 && hydration.every(Boolean),
    no_browser_errors: noBrowserErrors,
    no_destructive_mutation_attempts: destructiveAttempts.length === 0,
    world_state_monotonic: worldRemainsValid,
    transient_server_5xx: errors.some(e => /HTTP 5\d\d:/.test(e))
  },
  hydration,
  snapshots,
  errors
};
fs.writeFileSync("artifacts/aion-lifecycle-report.json", JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
process.exitCode = result.ok ? 0 : 1;
