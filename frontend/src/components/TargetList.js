import React from 'react';
import PropTypes from 'prop-types';
import styles from './TargetList.module.css';

/**
 * TargetList Component
 * Displays a list of targeted players for the draft with options to remove them.
 * 
 * @param {Object} props - Component props
 * @param {Array<string>} props.targetList - List of player names in the target list
 * @param {Function} props.setTargetList - Function to update the target list state
 * @param {Object} props.staticPlayerData - Object containing player data keyed by normalized name
 * @param {Function} props.handleRemoveFromTargets - Function to remove a player from the target list
 * @param {Function} props.getOverallSdLabel - Function to get consensus label for overall SD
 * @param {Function} props.getPositionalSdLabel - Function to get consensus label for positional SD
 */
const TargetList = ({ targetList, setTargetList, staticPlayerData, handleRemoveFromTargets, getOverallSdLabel, getPositionalSdLabel }) => {
  return (
    <section id="targets" className={styles.targetSection}>
      <div className={styles.toolHeader}>
        <h2>My Target List</h2>
        <p>A list of players you are targeting in your draft.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.targetListContainer}>
          {targetList.length > 0 ? (
            <table className={styles.targetTable}>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Pos.</th>
                  <th>Team</th>
                  <th>ECR</th>
                  <th>SD</th>
                  <th>Bye</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {targetList.map(playerName => {
                  // Normalize the player name to match the key in staticPlayerData
                  const normalizedName = playerName.replace(/\s(Jr|Sr|[IVX]+)\.?$/i, '').trim().toLowerCase();
                  const playerData = staticPlayerData[normalizedName];
                  return (
                    <tr key={playerName}>
                      <td>
                        <a href={`/?tool=dossier&player=${encodeURIComponent(playerName)}`} className={styles.playerLink} target="_blank" rel="noopener noreferrer">
                          {playerName}
                        </a>
                      </td>
                      <td>{playerData?.position || 'N/A'}</td>
                      <td>{playerData?.team || 'N/A'}</td>
                      <td>{playerData?.ecr_overall ? playerData.ecr_overall.toFixed(1) : 'N/A'}</td>
                      <td>
                        {playerData?.sd_overall ? (
                          <>
                            {playerData.sd_overall.toFixed(2)}
                            {getOverallSdLabel && getOverallSdLabel(playerData.sd_overall).icon && ` ${getOverallSdLabel(playerData.sd_overall).icon} ${getOverallSdLabel(playerData.sd_overall).label}`}
                          </>
                        ) : 'N/A'}
                      </td>
                      <td>{playerData?.bye_week || 'N/A'}</td>
                      <td>
                        <button 
                          className={styles.removeBtnSmall} 
                          onClick={() => handleRemoveFromTargets(playerName)}
                          aria-label={`Remove ${playerName} from target list`}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                          </svg>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p className={styles.emptyMessage}>Your target list is empty. Add players from the Dossier, Rankings, or Tiers tools.</p>
          )}
        </div>
      </div>
    </section>
  );
};

TargetList.propTypes = {
  targetList: PropTypes.arrayOf(PropTypes.string).isRequired,
  setTargetList: PropTypes.func.isRequired,
  staticPlayerData: PropTypes.object.isRequired,
  handleRemoveFromTargets: PropTypes.func.isRequired,
  getOverallSdLabel: PropTypes.func.isRequired,
  getPositionalSdLabel: PropTypes.func.isRequired,
};

export default TargetList;
