import React from 'react';
import styles from './MarketInefficiencyFinder.module.css';

export default function MarketInefficiencyFinder({
  marketInefficiencies,
  findMarketInefficiencies,
  handleAddToTargets,
  getOverallSdLabel,
}) {
  return (
    <section id="market" className={styles.marketSection}>
      <div className={styles.toolHeader}>
        <h2>Market Inefficiency Finder</h2>
        <p>Discover potential sleepers and busts by comparing data sources.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <select id="market-pos" className={styles.select}>
            <option value="all">All</option>
            <option value="QB">QB</option>
            <option value="RB">RB</option>
            <option value="WR">WR</option>
            <option value="TE">TE</option>
          </select>
          <button onClick={findMarketInefficiencies} className={styles.button}>Find</button>
        </div>
      </div>
      <div id="market-loader" className={styles.loader} style={{ display: 'none' }}></div>
      <div className={styles.marketResults}>
        <div className={styles.marketColumn}>
          <h3>Sleepers (Undervalued)</h3>
          {marketInefficiencies.sleepers.length > 0 ? marketInefficiencies.sleepers.map((player, index) => (
            <div key={`sleeper-${index}`} className={`${styles.analysisCard} ${styles.sleeper}`}>
              <div className={styles.analysisCardHeader}>
                <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className={styles.playerLink}>{player.name}</a></h4>
                <span className={`${styles.confidenceBadge} ${styles[player.confidence]}`}>{player.confidence}</span>
                <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
              </div>
              <div className={styles.playerDetailsGrid}>
                <span>ECR: {typeof player.ecr === 'number' ? player.ecr.toFixed(1) : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof player.sd === 'number' ? player.sd.toFixed(2) : 'N/A'}`}>
                  SD: {getOverallSdLabel(player.sd).icon} {getOverallSdLabel(player.sd).label}
                </span>
                <span>Best: {player.best || 'N/A'}</span>
                <span>Worst: {player.worst || 'N/A'}</span>
                <span>Rank Delta: {typeof player.rank_delta === 'number' ? player.rank_delta.toFixed(1) : 'N/A'}</span>
                <span>Rookie: {player.is_rookie ? 'Yes' : 'No'}</span>
              </div>
              <p>{player.justification}</p>
            </div>
          )) : <p>No sleepers found.</p>}
        </div>
        <div className={styles.marketColumn}>
          <h3>Busts (Overvalued)</h3>
          {marketInefficiencies.busts.length > 0 ? marketInefficiencies.busts.map((player, index) => (
            <div key={`bust-${index}`} className={`${styles.analysisCard} ${styles.bust}`}>
              <div className={styles.analysisCardHeader}>
                <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className={styles.playerLink}>{player.name}</a></h4>
                <span className={`${styles.confidenceBadge} ${styles[player.confidence]}`}>{player.confidence}</span>
                <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
              </div>
              <div className={styles.playerDetailsGrid}>
                <span>ECR: {typeof player.ecr === 'number' ? player.ecr.toFixed(1) : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof player.sd === 'number' ? player.sd.toFixed(2) : 'N/A'}`}>
                  SD: {getOverallSdLabel(player.sd).icon} {getOverallSdLabel(player.sd).label}
                </span>
                <span>Best: {player.best || 'N/A'}</span>
                <span>Worst: {player.worst || 'N/A'}</span>
                <span>Rank Delta: {typeof player.rank_delta === 'number' ? player.rank_delta.toFixed(1) : 'N/A'}</span>
                <span>Rookie: {player.is_rookie ? 'Yes' : 'No'}</span>
              </div>
              <p>{player.justification}</p>
            </div>
          )) : <p>No busts found.</p>}
        </div>
      </div>
    </section>
  );
}
