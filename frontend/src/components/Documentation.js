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
        <h2>Market Inefficiency Finder</h2>
        <p>Identify sleepers and busts. In Yahoo‑enhanced mode (when authenticated), results reflect your league context.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Select a position and run the analysis.</li>
          <li>Review the concise notes to spot value or avoid traps.</li>
        </ol>
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

      <section id="settings" className="doc-section">
        <h2>Settings</h2>
        <p>Manage your preferences. Set your Gemini API key (for AI), switch themes, and reset local data. Yahoo login is available from the sidebar.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Enter your Gemini API key to enable richer AI analysis.</li>
          <li>Toggle dark/light theme as preferred.</li>
          <li>Use Reset to clear local storage (API key, targets, etc.).</li>
        </ol>
      </section>
    </div>
  );
};

export default Documentation;
