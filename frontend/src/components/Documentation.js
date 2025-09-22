import React, { useEffect } from 'react';
import './Documentation.module.css'; // Assuming a CSS module for styling

const Documentation = () => {
  useEffect(() => {
    // Scroll to the specific section if a hash is present in the URL
    const hash = window.location.hash;
    if (hash) {
      const element = document.getElementById(hash.substring(1));
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, []);

  return (
    <div className="documentation-container">
      <h1>App Documentation</h1>
      <p>Welcome to RATM. This guide explains how to use each tool at a glance. It focuses on what you do and what the AI shows, without going into distracting detail.</p>

      <section id="navigation" className="doc-section">
        <h2>Navigation & Modes</h2>
        <ul>
          <li><strong>Season Mode:</strong> Use the sidebar switch to view <em>In‑Season</em> or <em>Pre‑Season</em> tools. Turn on “Show All” to see both groups at once.</li>
          <li><strong>Quick Actions:</strong> At the top of the sidebar, use the Dossier search box and shortcut chips for <em>Sit/Start</em> and <em>Waiver</em>. A Yahoo status chip indicates if you’re connected.</li>
          <li><strong>Recent Dossiers:</strong> The last few players you looked up appear as chips; click one to open the Player Dossier for that player immediately.</li>
        </ul>
      </section>

      <section id="player-dossier" className="doc-section">
        <h2>Player Dossier</h2>
        <p>The Player Dossier gives a fast, structured view of a player, plus a concise AI take. Sections appear in this order: Quick Scan → Player Overview → Expert Consensus & Rankings → AI Analysis → Weekly Outlook → Market/Ownership → Age/Trajectory.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Type a player name and click Generate.</li>
          <li>Skim Quick Scan and the AI Analysis for the takeaways; open details only if needed.</li>
          <li>Use the Add to Target List button to save players you’re tracking.</li>
        </ol>
      </section>

      <section id="rookie-rankings" className="doc-section">
        <h2>Rookie Rankings</h2>
        <p>This section provides rankings and analysis specifically for rookie players. It helps you identify promising new talent for your dynasty or redraft leagues, often including consensus scores and potential outlooks.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Select the desired position (e.g., QB, RB, WR, TE).</li>
          <li>Click "Generate Rookie Rankings" to see the list.</li>
          <li>Analyze the rankings and consensus scores to inform your draft decisions.</li>
        </ol>
      </section>

      <section id="positional-tiers" className="doc-section">
        <h2>Positional Tiers</h2>
        <p>The Positional Tiers tool helps you visualize player groupings within specific positions, making it easier to identify drop-offs in talent during your draft. This is crucial for understanding when to target certain positions.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Select the position you want to analyze.</li>
          <li>Click "Generate Tiers" to display the tiered rankings.</li>
          <li>Use these tiers to guide your draft strategy, ensuring you don't miss out on top-tier talent.</li>
        </ol>
      </section>

      <section id="target-list" className="doc-section">
        <h2>Target List</h2>
        <p>Keep track of players you're interested in drafting or acquiring. The Target List allows you to compile a personalized list of players and monitor their status, helping you stay organized throughout the season.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Add players to your Target List from other sections (e.g., Player Dossier).</li>
          <li>View your complete list in this section.</li>
          <li>Remove players from your list as needed.</li>
        </ol>
      </section>

      <section id="market-inefficiency-finder" className="doc-section">
        <h2>Sleepers & Traps (Market Inefficiency)</h2>
        <p>
          In‑season, this tool surfaces <strong>Sleepers</strong> (available FA/W players with upside this week) and
          <strong> Traps (Avoid)</strong> (available players likely to underperform replacement).
          When Yahoo‑connected, it uses your league data and <em>excludes your roster</em> from suggestions. Analysis is concise and human‑readable.
        </p>
        <h3>How to Use</h3>
        <ol>
          <li>Pick <em>All</em> or a specific position from the selector, then click Find.</li>
          <li>Each card shows a brief headline and up to 3 reasons (Projection edge, Trend, Consensus, Waivers).</li>
          <li>Availability chips indicate Free Agent or Waivers (with a clear time when provided by Yahoo).</li>
          <li>Yahoo mode is enabled by default in‑season; turn it off to run a general, non‑league analysis.</li>
        </ol>
        <p>
          Notes: Sleepers require a small projection edge over a position baseline and reasonable ownership; Traps require
          below‑baseline projections and negative signals. Your roster is automatically filtered out when Yahoo is connected.
        </p>
      </section>

      <section id="keeper-evaluator" className="doc-section">
        <h2>Keeper Evaluator</h2>
        <p>For keeper leagues, this tool helps you determine the optimal players to keep based on their draft cost and projected value. It provides an analysis to maximize your team's potential.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Add players you are considering keeping, along with their draft round cost.</li>
          <li>Click "Evaluate Keepers" to receive an analysis of their value.</li>
          <li>Make informed decisions about your keeper selections.</li>
        </ol>
      </section>

      <section id="trade-analyzer" className="doc-section">
        <h2>Trade Analyzer</h2>
        <p>Evaluate potential trades by inputting players from both sides of a proposed deal. The Trade Analyzer provides an objective assessment of the trade's fairness and impact on your team.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Enter players involved in the trade for both your team and the other team.</li>
          <li>Click "Analyze Trade" to get a detailed breakdown.</li>
          <li>Use the analysis to negotiate or accept/decline trades.</li>
        </ol>
      </section>

      <section id="draft-assistant" className="doc-section">
        <h2>Draft Assistant</h2>
        <p>Use during drafts to stay organized and make optimal picks based on roster needs and tiers.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Set up the board and update picks as the draft progresses.</li>
          <li>Use tiers and roster indicators to guide each selection.</li>
        </ol>
      </section>

      <section id="trending-players" className="doc-section">
        <h2>Trending Players</h2>
        <p>Quickly see who’s being added/dropped — a simple pulse on market moves to inform waivers and trades.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Scan the list and sort by adds/drops to spot momentum.</li>
        </ol>
      </section>

      <section id="trade-center" className="doc-section">
        <h2>Trade Center (Yahoo)</h2>
        <p>
          Trade Center generates tailored trade ideas using your actual Yahoo league snapshot. We prioritize the
          teams that need your surplus positions, then run a capped beam search so you see a balanced mix of opponents.
          Each card shows the opponent, AI reasons (when enabled), parity, and acceptance context badges.
        </p>
        <h3>How to Use:</h3>
        <ol>
          <li>Connect Yahoo, pick your league/team, and adjust sliders if needed.</li>
          <li><strong>Horizon focus</strong> changes how we rank the list (quick gains ⇄ rest of season); it does not change the proposal pool.</li>
          <li><strong>Acceptance minimum</strong> hides low-probability ideas. If everything falls below the bar, we still surface the closest fits and call that out.</li>
          <li>The toggle now reads <em>“Relax filters &amp; enable debug view”</em>: it lowers the filters, logs extra context, and unlocks lineup aftermath details.</li>
        </ol>
        <h3>What to Expect:</h3>
        <ul>
          <li>Opponent mix: each team can contribute at most a few proposals (top 4 or top_k/3) and repeated trades incur a diversity penalty, so the list isn’t dominated by one roster.</li>
          <li>Metadata includes per-opponent counts (shown in the UI and the API) so you can sanity check the distribution.</li>
          <li>Hover tooltips and badges translate parity/acceptance into plain English so you know when an offer is even, close, or a long shot.</li>
        </ul>
      </section>

      <section id="waiver-wire-assistant" className="doc-section">
        <h2>Waiver Wire Assistant</h2>
        <p>Make add/drop decisions with recommendations first. In Yahoo mode (default if authenticated), suggestions reflect your actual roster and available players.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>(Yahoo mode) Click “Refresh Recommendations”. Select a league if needed.</li>
          <li>Review cards: Add/Drop with a small benefit pill and “Why” bullets by default.</li>
          <li>Open “Show details” to see Estimated Benefit (overall roster score gain) and other numbers.</li>
          <li>Use “Alternatives” to see near‑neutral, context‑driven ideas; “Browse Pool” to explore manually.</li>
        </ol>
      </section>

      <section id="sit-start-optimizer" className="doc-section">
        <h2>Sit/Start Optimizer (Yahoo)</h2>
        <p>Optimize your weekly lineup using deterministic projections and grounded AI notes. Requires Yahoo login so we can read your roster.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Login with Yahoo in the sidebar. Open “Sit/Start Optimizer”. Pick a league and (optionally) a week.</li>
          <li>Click “Optimize My Lineup”. We suggest a starter for each slot and show any changes.</li>
          <li>Read the structured note: headline, reason bullets with chips (e.g., Projection, Matchup, Overall ECR), and a small score breakdown row.</li>
        </ol>
        <h3>What the Note Means</h3>
        <ul>
          <li><strong>Headline:</strong> The key change and estimated points gained.</li>
          <li><strong>Reasons:</strong> Up to three grounded bullets — examples: Projection edge, Easier/Tougher matchup (by opponent vs position), Overall ECR context, Usage (targets/snaps), Confidence (grades), Flex Fit.</li>
          <li><strong>Tags:</strong> Quick chips summarizing the signals (Projection Edge, Favorable Matchup, Consensus, etc.).</li>
          <li><strong>Score breakdown:</strong> Projection plus small nudges for matchup (±0.10), correlation, and variance where applicable.</li>
        </ul>
        <h3>How Data Is Used</h3>
        <ul>
          <li><strong>Projections:</strong> Weekly PPR projections drive selection. We exclude BYE/OUT; Q/D are allowed but flagged.</li>
          <li><strong>Matchup:</strong> Opponent and home/away are shown. If the opponent’s defense rates easier or tougher for the player’s position (Easy/Moderate/Tough), we add a small numeric nudge and a clear reason (e.g., Easier matchup this week: WR vs ARI (Easy)).</li>
          <li><strong>ECR semantics:</strong> Lower rank is better. For cross‑position decisions (flex), we compare overall ECR; for same‑position decisions, we compare weekly positional rank. We never compare positional ranks across positions.</li>
        </ul>
        <p>Notes are strictly grounded. If a field isn’t available (e.g., usage), we omit that reason rather than guessing.</p>
      </section>

      <section id="settings" className="doc-section">
        <h2>Settings</h2>
        <p>Manage your preferences. Set your Gemini API key (for AI), switch themes, and reset local data. Yahoo login is available from the sidebar.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Enter your Gemini API key to enable richer AI analysis.</li>
          <li>Toggle dark/light theme as preferred.</li>
          <li>Use Reset to clear local storage (API key, targets, etc.).</li>
        </ol>
        <h3>Data Health</h3>
        <ul>
          <li><strong>Diagnostics:</strong> Shows CSV freshness, weekly projections latest scrape, and match rates for roster and waivers.</li>
          <li><strong>Refresh Data (Admin):</strong> For local/dev, re‑download CSVs and rebuild caches, then re‑check diagnostics.</li>
        </ul>
      </section>
    </div>
  );
};

export default Documentation;
