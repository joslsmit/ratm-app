const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const tokenJson = process.env.YAHOO_TOKEN_JSON; // full JSON string from localStorage
  const leagueKey = process.env.LEAGUE_KEY;       // e.g., "461.l.42889"
  const url = process.env.APP_URL || 'http://localhost:3000/#waiver';

  if (!tokenJson) {
    console.error('Missing YAHOO_TOKEN_JSON env var. Provide the exact JSON string stored in localStorage as yahoo_token.');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  page.on('console', msg => console.log('[console]', msg.text()));
  page.on('response', async resp => {
    try {
      const u = resp.url();
      if (u.includes('/yahoo/waiver_recommendations_v2')) {
        const json = await resp.json().catch(() => null);
        if (json) {
          fs.writeFileSync('waiver_recommendations.json', JSON.stringify(json, null, 2));
          console.log('[recommendations] saved to waiver_recommendations.json');
        } else {
          const text = await resp.text().catch(() => '');
          fs.writeFileSync('waiver_recommendations_raw.txt', text);
        }
      }
    } catch (_) {}
  });

  console.log('Navigating to', url);
  await page.goto(url, { waitUntil: 'domcontentloaded' });

  // Set required localStorage items, then reload to let the app pick up Yahoo mode
  await page.evaluate((t) => localStorage.setItem('yahoo_token', t), tokenJson);
  await page.evaluate(() => localStorage.setItem('geminiApiKey', 'dummy-key-for-headless'));
  await page.reload({ waitUntil: 'domcontentloaded' });

  // Wait for league selector (if present) and choose league if provided
  try {
    await page.waitForSelector('select', { timeout: 5000 });
    if (leagueKey) {
      await page.selectOption('select', leagueKey).catch(() => {});
    }
  } catch (_) {
    console.log('No league selector found (may have auto-selected or only one league).');
  }

  // Click Get Waiver Recommendations
  const buttonText = 'Get Waiver Recommendations';
  await page.waitForTimeout(500);
  await page.getByText(buttonText, { exact: true }).click();

  // Wait for results or error
  await page.waitForSelector('.recCard, .errorText, .emptyState', { timeout: 20000 }).catch(() => {});

  // Capture screenshot and DOM
  await page.screenshot({ path: 'waiver_page.png', fullPage: true });
  fs.writeFileSync('waiver_dom.html', await page.content());

  await browser.close();
  console.log('Saved waiver_page.png, waiver_dom.html, and (if present) waiver_recommendations.json');
})().catch(err => {
  console.error('Playwright error:', err);
  process.exit(1);
});
