import { useState, useCallback, useContext } from 'react';
import { AppContext } from '../context/AppContext';

export const useApi = () => {
  const { userApiKey, ecrTypePreference, API_BASE_URL, setShowApiKeyModal } = useContext(AppContext);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const makeApiRequest = useCallback(async (endpoint, body) => {
    if (!userApiKey) {
      alert('API Key not found. Please enter your key.');
      setShowApiKeyModal(true);
      return null;
    }
    if (!endpoint || typeof endpoint !== 'string') {
      return null;
    }
    
    setIsLoading(true);
    setError(null);
    
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': userApiKey
        },
        body: JSON.stringify({ ...body, ecr_type_preference: ecrTypePreference }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `An unknown server error occurred on endpoint: ${endpoint}`);
      }
      
      const data = await response.json();
      setIsLoading(false);
      return data;
      
    } catch (err) {
      setError(err);
      setIsLoading(false);
      throw err;
    }
  }, [userApiKey, ecrTypePreference, API_BASE_URL, setShowApiKeyModal]);

  return { makeApiRequest, isLoading, error };
};
