import React from 'react';
import styles from './RookieRankings.module.css';

export default function RookieRankings({
  rookieRankings,
  generateRookieRankings,
  handleAddToTargets,
  getRookieSdLabel,
}) {
  return (
    <section id="rookie" className={styles.rookieSection}>
      <div className={styles.toolHeader}>
        <h2>2025 Rookie Rankings</h2>
        <p>Get AI-powered rankings and analysis for the incoming rookie class.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <select id="rookie-pos" className={styles.select}>
            <option value="all">All</option>
            <option value="QB">QB</option>
            <option value="RB">RB</option>
            <option value="WR">WR</option>
            <option value="TE">TE</option>
          </select>
          <button onClick={generateRookieRankings} className={styles.button}>Generate</button>
        </div>
      </div>
      <div id="rookie-loader" className={styles.loader} style={{ display: 'none' }}></div>
      <div className={styles.resultBoxCards}>
        {rookieRankings.length > 0 ? rookieRankings.map((rookie, index) => (
          <div key={index} className={styles.rookieCard}>
            <div className={styles.rookieHeader}>
              <h3>
                <a href={`/?tool=dossier&player=${encodeURIComponent(rookie.name)}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                  {rookie.name}
                </a> ({rookie.position}, {rookie.team || 'N/A'})
              </h3>
              <div className={styles.rookieActions}>
                <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(rookie.name)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
                <span className={styles.rank}>#{rookie.rank}</span>
              </div>
            </div>
            <div className={styles.rookieDetails}>
              <span title="Expert Consensus Ranking for rookies">Rookie ECR: {typeof rookie.ecr === 'number' ? rookie.ecr.toFixed(1) : 'N/A'}</span>
              <span title={`Standard Deviation: ${typeof rookie.sd === 'number' ? rookie.sd.toFixed(2) : 'N/A'}`}>
                SD: {getRookieSdLabel(rookie.sd).icon} {getRookieSdLabel(rookie.sd).label}
              </span>
              <span>Best: {rookie.best || 'N/A'}</span>
              <span>Worst: {rookie.worst || 'N/A'}</span>
              <span>Rank Delta: {typeof rookie.rank_delta === 'number' ? rookie.rank_delta.toFixed(1) : 'N/A'}</span>
            </div>
            <p className={styles.rookieAnalysis}>{rookie.analysis}</p>
          </div>
        )) : <p>No rookie rankings to display. Generate a new list.</p>}
      </div>
    </section>
  );
}
