import React from 'react';
import styles from './EmptyState.module.css';

const EmptyState = ({ title, message }) => {
  return (
    <div className={styles.emptyState}>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
};

export default EmptyState;
