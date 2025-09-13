# Headless Browser Testing — Playwright Quick Guide

> Purpose: Enable self‑serve validation of UI order/behavior and API JSON, without manual screenshots or copy/paste. Used for Waiver and Dossier checks.

## Why
- Reproduce the exact DOM/section order the browser renders (CSS flex order vs JSX).
- Capture recommendation JSON and debug prompts safely, without storing secrets in files.

## Playwright (Chromium) — One‑off Script

Example: Verify Dossier section order for a player.

```
# From repo root
cd frontend
node -e '
(async()=>{
  const { chromium } = require("playwright");
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ ignoreHTTPSErrors: true });
  const p = await ctx.newPage();
  await p.goto("http://localhost:3000/?tool=dossier&player=Tyreek%20Hill", { waitUntil: "domcontentloaded" });
  await p.waitForTimeout(800);
  try { await p.waitForSelector("#dossier .dossierOutput .card h3", { timeout: 15000 }); } catch(_) {}
  const order = await p.$$eval("#dossier .dossierOutput .card h3", hs => hs.map(h => h.textContent.trim()));
  console.log("Dossier section order:", JSON.stringify(order, null, 2));
  await b.close();
})();'
```

- Output prints the H3 headings in the order the browser renders them.
- This is read‑only; nothing is written to disk.

## Waiver Page — Capture AI Debug and JSON

```
# Assumes your browser has yahoo_token in localStorage. For headless, pass it via env.
# Never print or store tokens; pass in memory only.

export YAHOO_TOKEN_JSON='{"access_token":"<ya-token>"}'
node scripts/waiver_headless.js
# Produces console logs; script is configured to avoid writing secrets.
```

What the script does:
- Sets `localStorage.yahoo_token` at runtime in the headless page (not written to disk).
- Navigates to `/#waiver`, selects your league, clicks Refresh Recommendations.
- Logs any AI Debug information that the app exposes in the UI (prompt, counts).
- If you enable file outputs, ensure no tokens/keys are logged or saved.

## Safety Notes
- Do not serialize or save Authorization headers, tokens, or X‑API‑Key.
- If you temporarily save a prompt or JSON to a file, review it and delete immediately after validation.
- Our CI does not run Playwright; this is a local dev tool only.

## Gotchas
- macOS sandbox may block Chromium temp dirs in strict shells; if so, run with elevated perms or use the standalone Node script and let the app render an in‑page debug panel.
- CSS flex `order` overrides DOM order; inspecting headings with Playwright is the most reliable way to confirm visible section order.
