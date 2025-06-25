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
      <p>Welcome to the documentation for the Fantasy Football App. This guide explains how to use each section of the application to enhance your fantasy football experience.</p>

      <section id="player-dossier" className="doc-section">
        <h2>Player Dossier</h2>
        <p>The Player Dossier provides a comprehensive analysis of individual players. Enter a player's name to get detailed insights, including their Expert Consensus Ranking (ECR), positional tiers, and other relevant data points. This tool helps you quickly assess a player's value and potential.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Navigate to the "Player Dossier" section.</li>
          <li>Type the player's name into the search bar.</li>
          <li>Click "Generate Dossier" to view the analysis.</li>
          <li>You can also add players directly to your Target List from here.</li>
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
        <p>Identify players who are undervalued (sleepers) or overvalued (busts) by the market. This tool leverages data to highlight discrepancies between expert consensus and potential performance, giving you an edge.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Select a position to analyze.</li>
          <li>Click "Find Inefficiencies" to see potential sleepers and busts.</li>
          <li>Use this information to find value picks or avoid overpaying for players.</li>
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
        <p>Your real-time companion during the draft. The Draft Assistant helps you make optimal picks by providing recommendations based on your league settings, roster needs, and player availability.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Set up your league details and draft board.</li>
          <li>As players are drafted, input them into the assistant.</li>
          <li>Receive real-time recommendations for your next pick.</li>
        </ol>
      </section>

      <section id="trending-players" className="doc-section">
        <h2>Trending Players</h2>
        <p>Stay updated on players whose stock is rising or falling. This section shows recent trends in player interest, often reflecting news, injuries, or performance changes.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>View the list of trending players.</li>
          <li>Sort by different metrics (e.g., adds, drops) to see what's hot or not.</li>
          <li>Use this information to make timely waiver wire claims or trade offers.</li>
        </ol>
      </section>

      <section id="waiver-wire-assistant" className="doc-section">
        <h2>Waiver Wire Assistant</h2>
        <p>Optimize your waiver wire claims. This tool helps you decide which players to drop and which to add, providing analysis on the impact of potential roster changes.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Input your current roster.</li>
          <li>Specify the player you want to add from waivers.</li>
          <li>Click "Analyze Waiver Swap" to get a recommendation.</li>
        </ol>
      </section>

      <section id="settings" className="doc-section">
        <h2>Settings</h2>
        <p>Manage your application preferences, including your Google Gemini API key, theme settings, and options to reset your saved data.</p>
        <h3>How to Use:</h3>
        <ol>
          <li>Access this section to update your API key.</li>
          <li>Toggle between dark and light themes.</li>
          <li>Use the "Reset Application" button to clear all local data (use with caution).</li>
        </ol>
      </section>
    </div>
  );
};

export default Documentation;
