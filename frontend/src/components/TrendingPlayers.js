import React, { useState } from 'react';
import styles from './TrendingPlayers.module.css';

function TrendingPlayers({ trendingData, sortTrendingData }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  if (!trendingData || trendingData.length === 0) {
    return <p className={styles.noData}>No trending players data available.</p>;
  }

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortKey === key && sortDirection === 'asc') {
      direction = 'desc';
    }
    setSortKey(key);
    setSortDirection(direction);
    sortTrendingData(key, direction);
  };

  const renderSortIcon = (key) => {
    if (sortKey !== key) {
      return <span aria-label="sortable column" role="img" className={styles.sortIcon}>⇅</span>;
    }
    return sortDirection === 'asc' ? (
      <span aria-label="sorted ascending" role="img" className={styles.sortIcon}>⬆️</span>
    ) : (
      <span aria-label="sorted descending" role="img" className={styles.sortIcon}>⬇️</span>
    );
  };

  return (
    <section id="trending" className={styles.trendingSection}>
      <div className={styles.toolHeader}>
        <h2>Trending Players</h2>
        <p>Players currently trending in your league.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.gridTable}>
          <div className={styles.gridHeader}>
            <div className={styles.sortable} onClick={() => handleSort('name')} title="Sort by Player Name">
              Player {renderSortIcon('name')}
            </div>
            <div className={styles.sortable} onClick={() => handleSort('position')} title="Sort by Position">
              Pos. {renderSortIcon('position')}
            </div>
            <div className={styles.sortable} onClick={() => handleSort('team')} title="Sort by Team">
              Team {renderSortIcon('team')}
            </div>
            <div className={styles.sortable} onClick={() => handleSort('adds')} title="Sort by Adds">
              Adds {renderSortIcon('adds')}
            </div>
            <div className={styles.sortable} onClick={() => handleSort('ecr')} title="Sort by ECR">
              ECR {renderSortIcon('ecr')}
            </div>
          </div>
          {trendingData.map((player, index) => (
            <div key={index} className={styles.gridRow} tabIndex={0}>
              <div className={styles.playerNameCell}>
                <a 
                  href={`/?tool=dossier&player=${encodeURIComponent(player.name || player.player_name || '')}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className={styles.playerLink}
                >
                  {player.name || player.player_name || 'N/A'}
                </a>
              </div>
              <div>{player.position || 'N/A'}</div>
              <div>{player.team || 'N/A'}</div>
              <div>{player.adds != null ? player.adds : 'N/A'}</div>
              <div>{player.ecr != null ? player.ecr : 'N/A'}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default TrendingPlayers;
