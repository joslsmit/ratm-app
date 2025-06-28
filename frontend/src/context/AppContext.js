import React, { createContext, useState, useEffect, useCallback, useMemo } from 'react';
import showdown from 'showdown';

const API_BASE_URL = 'http://localhost:5001/api';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  // State for API Key and Modal
  const [userApiKey, setUserApiKey] = useState(() => localStorage.getItem('geminiApiKey') || '');
  const [showApiKeyModal, setShowApiKeyModal] = useState(() => !localStorage.getItem('geminiApiKey'));

  // State for active tool and data
  const [activeTool, setActiveTool] = useState('dossier');
  const [allPlayers, setAllPlayers] = useState([]);
  const [staticPlayerData, setStaticPlayerData] = useState({});
  const [trendingData, setTrendingData] = useState([]);
  const [marketInefficiencies, setMarketInefficiencies] = useState({ sleepers: [], busts: [] });
  const [rookieRankings, setRookieRankings] = useState([]);
  const [dossierResult, setDossierResult] = useState(null);
  const [tiersResult, setTiersResult] = useState([]);
  const [keeperResult, setKeeperResult] = useState('');
  const [waiverSwapResult, setWaiverSwapResult] = useState('');
  const [isWaiverSwapLoading, setIsWaiverSwapLoading] = useState(false);
  const [lastUpdateDate, setLastUpdateDate] = useState('Loading...');

  // States for list-based tools
  const [targetList, setTargetList] = useState([]);

  const [ecrTypePreference, setEcrTypePreference] = useState('overall');

  const converter = useMemo(() => new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true }), []);

  const saveApiKey = (key) => {
    if (key) {
      setUserApiKey(key);
      localStorage.setItem('geminiApiKey', key);
      setShowApiKeyModal(false);
    } else {
      alert('Please enter a valid API key.');
    }
  };

  useEffect(() => {
    fetch(`${API_BASE_URL}/all_player_names_with_data`)
      .then(response => response.json())
      .then(data => {
        if (data && Array.isArray(data)) {
          setAllPlayers(data.map(p => p.autocomplete_name));
          const staticData = data.reduce((acc, p) => {
            if (p.name) {
              acc[p.name.toLowerCase()] = p;
            }
            return acc;
          }, {});
          setStaticPlayerData(staticData);
        }
      })
      .catch(error => console.error("Error fetching player names:", error));
  }, []);

  const value = {
    userApiKey,
    showApiKeyModal,
    saveApiKey,
    activeTool,
    setActiveTool,
    allPlayers,
    staticPlayerData,
    trendingData,
    setTrendingData,
    marketInefficiencies,
    setMarketInefficiencies,
    rookieRankings,
    setRookieRankings,
    dossierResult,
    setDossierResult,
    tiersResult,
    setTiersResult,
    keeperResult,
    setKeeperResult,
    waiverSwapResult,
    setWaiverSwapResult,
    isWaiverSwapLoading,
    setIsWaiverSwapLoading,
    lastUpdateDate,
    setLastUpdateDate,
    targetList,
    setTargetList,
    ecrTypePreference,
    setEcrTypePreference,
    converter,
    API_BASE_URL,
    setShowApiKeyModal
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
