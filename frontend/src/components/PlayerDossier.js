import React from 'react';
import styles from './PlayerDossier.module.css';

export default function PlayerDossier({
  dossierResult,
  generateDossier,
  handleAddToTargets,
  getEstimatedDraftRound,
  getOverallSdLabel,
  getPositionalSdLabel,
  converter,
}) {
  return (
    <section id="dossier" className={styles.dossierSection}>
      <div className={styles.toolHeader}>
        <h2>Player Dossier</h2>
        <p>Get a complete 360-degree scouting report on any player.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <div className={styles.autoCompleteWrapper}>
            <input id="dossier-player-name" type="text" placeholder="Enter player name..." />
          </div>
          <button onClick={() => generateDossier()}>Generate</button>
        </div>
      </div>
      <div id="dossier-loader" className={styles.loader} style={{ display: 'none' }}></div>
      {dossierResult && !dossierResult.error && (
        <div className={styles.dossierOutput}>
          <div className={`${styles.card} ${styles.playerOverviewCard}`}>
            <div className={styles.dossierTitleContainer}>
              <h3>{dossierResult.player_data.name}</h3>
              <button 
                className={`${styles.addTargetBtn}`} 
                title="Add to Target List" 
                onClick={() => {
                  handleAddToTargets(dossierResult.player_data.name);
                  // Temporarily add the 'added' class for visual feedback
                  const button = document.querySelector(`.${styles.addTargetBtn}`);
                  if (button) {
                    button.classList.add(styles.added);
                    setTimeout(() => {
                      button.classList.remove(styles.added);
                    }, 2000); // Revert after 2 seconds
                  }
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-plus-circle"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
              </button>
            </div>
            <div className={styles.playerBasicInfo}>
              <span><strong>Team:</strong> {dossierResult.player_data.team}</span>
              <span><strong>Position:</strong> {dossierResult.player_data.position}</span>
              <span><strong>Bye:</strong> {dossierResult.player_data.bye_week || 'N/A'}</span>
            </div>
          </div>

          <div className={`${styles.card} ${styles.ecrDataCard}`}>
            <h3>ECR & Rankings</h3>
            <div className={styles.ecrGrid}>
              <div className={styles.ecrColumn}>
                <h4>Overall ECR</h4>
                <span>ECR: {dossierResult.player_data.ecr_overall ? `${dossierResult.player_data.ecr_overall.toFixed(1)} (${getEstimatedDraftRound(dossierResult.player_data.ecr_overall)})` : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof dossierResult.player_data.sd_overall === 'number' ? dossierResult.player_data.sd_overall.toFixed(2) : 'N/A'}`}>
                  SD: {getOverallSdLabel(dossierResult.player_data.sd_overall).icon} {getOverallSdLabel(dossierResult.player_data.sd_overall).label}
                </span>
                <span>Best: {dossierResult.player_data.best_overall || 'N/A'}</span>
                <span>Worst: {dossierResult.player_data.worst_overall || 'N/A'}</span>
                <span>Rank Delta: {dossierResult.player_data.rank_delta_overall ? dossierResult.player_data.rank_delta_overall.toFixed(1) : 'N/A'}</span>
              </div>
              <div className={styles.ecrColumn}>
                <h4>Positional ECR</h4>
                <span>ECR: {dossierResult.player_data.ecr_positional ? dossierResult.player_data.ecr_positional.toFixed(1) : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof dossierResult.player_data.sd_positional === 'number' ? dossierResult.player_data.sd_positional.toFixed(2) : 'N/A'}`}>
                  SD: {getPositionalSdLabel(dossierResult.player_data.sd_positional).icon} {getPositionalSdLabel(dossierResult.player_data.sd_positional).label}
                </span>
                <span>Best: {dossierResult.player_data.best_positional || 'N/A'}</span>
                <span>Worst: {dossierResult.player_data.worst_positional || 'N/A'}</span>
                <span>Rank Delta: {dossierResult.player_data.rank_delta_positional ? dossierResult.player_data.rank_delta_positional.toFixed(1) : 'N/A'}</span>
              </div>
            </div>
          </div>

          <div className={`${styles.card} ${styles.aiAnalysisCard}`}>
            <h3>AI Analysis</h3>
            <div id="dossier-result" className={styles.resultBox} dangerouslySetInnerHTML={{ __html: converter.makeHtml(dossierResult.analysis) }}></div>
          </div>
        </div>
      )}
      {dossierResult && dossierResult.error && (
        <div className={styles.resultBox}>
          <p style={{ color: 'var(--danger-color)' }}>An error occurred: {dossierResult.error}</p>
        </div>
      )}
    </section>
  );
}
