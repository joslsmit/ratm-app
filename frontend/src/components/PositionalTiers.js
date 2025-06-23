import React from 'react';
import styles from './PositionalTiers.module.css';

export default function PositionalTiers({
  tiersResult,
  generateTiers,
  handleAddToTargets,
  getEstimatedDraftRound,
  getPositionalSdLabel,
}) {
  return (
    <section id="tiers" className={styles.tiersSection}>
      <div className={styles.toolHeader}>
        <h2>Positional Tiers</h2>
        <p>Generate tier-based rankings to understand value drop-offs.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <select id="tiers-pos" className={styles.select}>
            <option value="QB">QB</option>
            <option value="RB">RB</option>
            <option value="WR">WR</option>
            <option value="TE">TE</option>
          </select>
          <button onClick={generateTiers} className={styles.button}>Generate Tiers</button>
        </div>
      </div>
      <div id="tiers-loader" className={styles.loader} style={{ display: 'none' }}></div>
      <div className={styles.tiersOutput}>
        {tiersResult.length > 0 ? tiersResult.map((tier, tierIndex) => (
          <div key={tierIndex} className={styles.tierCard}>
            <h3>{tier.header}</h3>
            <p className={styles.tierSummary}>{tier.summary}</p>
            <div className={styles.tierPlayers}>
              {tier.players.map((player, playerIndex) => (
                <div key={playerIndex} className={styles.tierPlayerItem}>
                  <div className={styles.playerNameLink}>
                    <a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                      {player.name}
                    </a>
                    <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                    </button>
                  </div>
                  <div className={styles.playerDetailsGrid}>
                    <span>Pos: {player.position || 'N/A'}</span>
                    <span>Team: {player.team || 'N/A'}</span>
                    <span>
                      ECR: {typeof player.ecr === 'number' ? player.ecr.toFixed(1) : 'N/A'}
                      {typeof player.ecr === 'number' && ` (${getEstimatedDraftRound(player.ecr)})`}
                    </span>
                    <span title={`Standard Deviation: ${typeof player.sd === 'number' ? player.sd.toFixed(2) : 'N/A'}`}>
                      SD: {getPositionalSdLabel(player.sd).icon} {getPositionalSdLabel(player.sd).label}
                    </span>
                    <span>Best: {player.best || 'N/A'}</span>
                    <span>Worst: {player.worst || 'N/A'}</span>
                    <span>Rank Delta: {typeof player.rank_delta === 'number' ? player.rank_delta.toFixed(1) : 'N/A'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )) : <p className={styles.resultBox}>No tiers to display. Generate tiers for a position.</p>}
      </div>
    </section>
  );
}
