import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css'; // Import the main CSS file
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { AppProvider } from './context/AppContext';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppProvider>
        <App />
      </AppProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
