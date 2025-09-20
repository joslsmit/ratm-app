import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import styles from './TradeCenter.module.css';
import LoadingSpinner from './LoadingSpinner';
import EmptyState from './EmptyState';
import { AppContext } from '../context/AppContext';

const DEFAULT_MIN_ACCEPTANCE = 0.15;

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—';
  }
  return `${Math.round(Number(value) * 100)}%`;
};

const toDossierLink = (name) => {
  if (!name) return '#';
  return `/?tool=dossier&player=${encodeURIComponent(name)}`;
};

const TradeCenter = () => {
  const { API_BASE_URL, userApiKey, setShowApiKeyModal } = useContext(AppContext);

  const [yahooToken, setYahooToken] = useState(null);
  const [leagues, setLeagues] = useState([]);
  const [loadingLeagues, setLoadingLeagues] = useState(true);
  const [leagueError, setLeagueError] = useState('');

  const [selectedLeagueKey, setSelectedLeagueKey] = useState('');
  const [selectedTeamKey, setSelectedTeamKey] = useState('');
  const [teams, setTeams] = useState([]);
  const [loadingTeams, setLoadingTeams] = useState(false);

  const [selectedTargetKeys, setSelectedTargetKeys] = useState([]);
  const [includeInjured, setIncludeInjured] = useState(false);
  const [benchFirst, setBenchFirst] = useState(true);
  const [maxPackageSize, setMaxPackageSize] = useState(2);
  const [topK, setTopK] = useState(12);
  const [minAcceptance, setMinAcceptance] = useState(DEFAULT_MIN_ACCEPTANCE);
  const [horizonFocus, setHorizonFocus] = useState(50);
  const [debugMode, setDebugMode] = useState(false);

  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [proposals, setProposals] = useState([]);
  const [meta, setMeta] = useState(null);
  const [filteredOutCount, setFilteredOutCount] = useState(0);
  const [relaxedAcceptance, setRelaxedAcceptance] = useState(false);

  const [expandedTrades, setExpandedTrades] = useState([]);
  const [debugData, setDebugData] = useState({});
  const [debugLoading, setDebugLoading] = useState({});

  const authHeader = useMemo(() => {
    if (!yahooToken || !yahooToken.access_token) return null;
    return `Bearer ${yahooToken.access_token}`;
  }, [yahooToken]);

  const availableTargets = useMemo(() => {
    if (!teams?.length) return [];
    return teams.filter((team) => team.team_key !== selectedTeamKey);
  }, [teams, selectedTeamKey]);

  const loadTokenFromHash = useCallback(() => {
    try {
      const hash = window.location.hash || '';
      if (!hash.includes('token=')) return null;
      const query = hash.slice(hash.indexOf('?') + 1);
      const params = new URLSearchParams(query);
      return params.get('token');
    } catch (error) {
      console.error('Failed to parse Yahoo token from hash:', error);
      return null;
    }
  }, []);

  useEffect(() => {
    const initializeToken = () => {
      let tokenObject = null;
      const tokenFromHash = loadTokenFromHash();

      if (tokenFromHash) {
        try {
          const decoded = decodeURIComponent(tokenFromHash);
          tokenObject = JSON.parse(decoded);
          localStorage.setItem('yahoo_token', decoded);
          const cleanHash = window.location.hash.split('?')[0];
          window.history.replaceState({}, document.title, `${window.location.pathname}${cleanHash}`);
        } catch (error) {
          console.error('Error decoding Yahoo token from hash:', error);
          setLeagueError('Failed to process Yahoo login. Please retry.');
        }
      }

      if (!tokenObject) {
        try {
          const stored = localStorage.getItem('yahoo_token');
          if (stored) {
            tokenObject = JSON.parse(stored);
          }
        } catch (error) {
          console.error('Error reading Yahoo token from storage:', error);
          setLeagueError('Stored Yahoo token was invalid. Please log in again.');
          localStorage.removeItem('yahoo_token');
        }
      }

      setYahooToken(tokenObject);
    };

    initializeToken();
  }, [loadTokenFromHash]);

  const fetchLeagues = useCallback(async () => {
    if (!authHeader) {
      setLoadingLeagues(false);
      return;
    }
    setLoadingLeagues(true);
    setLeagueError('');
    try {
      const response = await fetch(`${API_BASE_URL}/yahoo/leagues`, {
        headers: { Authorization: authHeader }
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Unable to fetch leagues.');
      }
      const data = await response.json();
      if (Array.isArray(data)) {
        setLeagues(data);
        if (data.length === 1) {
          setSelectedLeagueKey(data[0].league_key);
          setSelectedTeamKey(data[0].team_key || '');
        }
      } else {
        throw new Error('Unexpected leagues response.');
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
      if (error.message?.toLowerCase().includes('unauth') || error.message?.toLowerCase().includes('token')) {
        setLeagueError('Yahoo authentication expired. Please log in again.');
        localStorage.removeItem('yahoo_token');
        setYahooToken(null);
      } else {
        setLeagueError(error.message || 'Failed to load leagues.');
      }
    } finally {
      setLoadingLeagues(false);
    }
  }, [API_BASE_URL, authHeader]);

  useEffect(() => {
    if (authHeader) {
      fetchLeagues();
    }
  }, [authHeader, fetchLeagues]);

  const fetchLeagueSnapshot = useCallback(async (leagueKey) => {
    if (!leagueKey || !authHeader) {
      setTeams([]);
      return;
    }
    setLoadingTeams(true);
    try {
      const url = `${API_BASE_URL}/yahoo/league_snapshot?league_key=${encodeURIComponent(leagueKey)}`;
      const response = await fetch(url, { headers: { Authorization: authHeader } });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Unable to fetch league snapshot.');
      }
      const data = await response.json();
      if (data && Array.isArray(data.teams)) {
        const normalizedTeams = data.teams.map((team) => ({
          team_key: team.team_key,
          name: team.name || team.team_key,
          roster: team.roster || []
        })).filter((team) => team.team_key);
        setTeams(normalizedTeams);
        if (normalizedTeams.length > 0) {
          const myTeamExists = normalizedTeams.some((team) => team.team_key === (leagues.find((l) => l.league_key === leagueKey)?.team_key));
          if (!myTeamExists && normalizedTeams[0]) {
            setSelectedTeamKey((prev) => prev || normalizedTeams[0].team_key);
          }
          const targetDefaults = normalizedTeams
            .filter((team) => team.team_key !== (leagues.find((l) => l.league_key === leagueKey)?.team_key))
            .map((team) => team.team_key);
          setSelectedTargetKeys(targetDefaults);
        }
      } else {
        setTeams([]);
      }
    } catch (error) {
      console.error('Error fetching league snapshot:', error);
      setTeams([]);
    } finally {
      setLoadingTeams(false);
    }
  }, [API_BASE_URL, authHeader, leagues]);

  useEffect(() => {
    if (selectedLeagueKey) {
      const league = leagues.find((l) => l.league_key === selectedLeagueKey);
      setSelectedTeamKey(league?.team_key || '');
      fetchLeagueSnapshot(selectedLeagueKey);
      setProposals([]);
      setMeta(null);
    }
  }, [selectedLeagueKey, leagues, fetchLeagueSnapshot]);

  const handleLeagueChange = (event) => {
    const value = event.target.value;
    setSelectedLeagueKey(value);
  };

  const handleTargetToggle = (teamKey) => {
    setSelectedTargetKeys((prev) => {
      if (prev.includes(teamKey)) {
        return prev.filter((key) => key !== teamKey);
      }
      return [...prev, teamKey];
    });
  };

  const handleSelectAllTargets = () => {
    setSelectedTargetKeys(availableTargets.map((team) => team.team_key));
  };

  const handleClearTargets = () => {
    setSelectedTargetKeys([]);
  };

  const computeScore = useCallback((proposal) => {
    const myDelta = Number(proposal.my_delta_points || 0);
    const acceptance = Number(proposal.acceptance_prob || 0);
    const aiAdj = Number(proposal.ai_rank_adjustment || 0);
    const benchBonus = proposal.flags?.includes('bench_target') ? 0.1 : 0;
    const horizonWeight = horizonFocus / 100; // 0 => ROS, 1 => short-term emphasis
    const deltaWeight = 0.6 + 0.4 * horizonWeight;
    const acceptanceWeight = 10 * (1 - 0.3 * horizonWeight);
    return myDelta * deltaWeight + acceptance * acceptanceWeight + aiAdj + benchBonus;
  }, [horizonFocus]);

  const displayProposals = useMemo(() => {
    if (!Array.isArray(proposals)) return [];
    return [...proposals].sort((a, b) => computeScore(b) - computeScore(a));
  }, [proposals, computeScore]);

  const handleGenerate = async () => {
    if (!authHeader || !yahooToken) {
      setLeagueError('Yahoo authentication required.');
      return;
    }
    if (!userApiKey) {
      setShowApiKeyModal(true);
      return;
    }
    if (!selectedLeagueKey || !selectedTeamKey) {
      setGenerateError('Select a league to generate proposals.');
      return;
    }

    setIsGenerating(true);
    setGenerateError('');
    setFilteredOutCount(0);

    try {
      const targetKeys = selectedTargetKeys;
      const body = {
        league_key: selectedLeagueKey,
        my_team_key: selectedTeamKey,
        include_injured: includeInjured,
        bench_first: benchFirst,
        max_package_size: Number(maxPackageSize),
        top_k: Number(topK),
        use_ai: true,
        gemini_api_key: userApiKey,
        debug: debugMode ? 1 : 0,
        horizon_focus: horizonFocus / 100,
        acceptance_floor: minAcceptance
      };

      if (targetKeys.length > 0 && targetKeys.length !== availableTargets.length) {
        body.target_team_keys = targetKeys;
      }

      const response = await fetch(`${API_BASE_URL}/trade_suggestions`, {
        method: 'POST',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
          'X-API-Key': userApiKey
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate trade suggestions.');
      }

      const data = await response.json();
      const rawProposals = Array.isArray(data.proposals) ? data.proposals : [];
      const filtered = rawProposals.filter((proposal) => Number(proposal.acceptance_prob || 0) >= minAcceptance - 1e-6);
      const usedProposals = filtered.length > 0 ? filtered : rawProposals;
      const hiddenCount = filtered.length > 0 ? Math.max(0, rawProposals.length - filtered.length) : 0;
      setFilteredOutCount(hiddenCount);
      setRelaxedAcceptance(filtered.length === 0 && rawProposals.length > 0);
      setProposals(usedProposals);
      setMeta(data.meta || null);
      setExpandedTrades([]);
      setDebugData({});
    } catch (error) {
      console.error('Trade generation failed:', error);
      setGenerateError(error.message || 'Trade generation failed.');
      setRelaxedAcceptance(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleDebugDetails = async (tradeId) => {
    const isExpanded = expandedTrades.includes(tradeId);
    if (isExpanded) {
      setExpandedTrades((prev) => prev.filter((id) => id !== tradeId));
      return;
    }

    setExpandedTrades((prev) => [...prev, tradeId]);

    if (debugData[tradeId] || !authHeader) return;

    setDebugLoading((prev) => ({ ...prev, [tradeId]: true }));
    try {
      const params = new URLSearchParams({
        league_key: selectedLeagueKey,
        my_team_key: selectedTeamKey,
        trade_id: tradeId,
        include_injured: includeInjured ? '1' : '0',
        bench_first: benchFirst ? '1' : '0'
      });
      const response = await fetch(`${API_BASE_URL}/trade_suggestions/debug?${params.toString()}`, {
        headers: { Authorization: authHeader }
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to load debug data.');
      }
      const data = await response.json();
      setDebugData((prev) => ({ ...prev, [tradeId]: data }));
    } catch (error) {
      console.error('Failed to load debug data:', error);
      setDebugData((prev) => ({ ...prev, [tradeId]: { error: error.message || 'Unable to load debug data.' } }));
    } finally {
      setDebugLoading((prev) => ({ ...prev, [tradeId]: false }));
    }
  };

  const resetFilters = () => {
    setIncludeInjured(false);
    setBenchFirst(true);
    setMaxPackageSize(2);
    setTopK(12);
    setMinAcceptance(DEFAULT_MIN_ACCEPTANCE);
    setHorizonFocus(50);
    setDebugMode(false);
    setFilteredOutCount(0);
    setRelaxedAcceptance(false);
  };

  if (!yahooToken) {
    return (
      <div className={styles.tradeCenter}>
        <EmptyState
          title="Yahoo login required"
          message="Connect your Yahoo fantasy account via the Yahoo Login tool to generate personalized trade ideas."
        />
      </div>
    );
  }

  return (
    <div className={styles.tradeCenter}>
      <header className={styles.headerRow}>
        <div>
          <h1>Trade Center</h1>
          <p className={styles.subtitle}>Personalized, negotiation-ready trade ideas for your Yahoo league.</p>
        </div>
        <div className={styles.metaChips}>
          {meta?.ai_enabled && (
            <span className={`${styles.chip} ${styles.chipSuccess}`}>AI explanations on</span>
          )}
          {typeof meta?.ai_latency_ms === 'number' && (
            <span className={styles.chip}>AI latency: {meta.ai_latency_ms} ms</span>
          )}
          {proposals.length > 0 && (
            <span className={styles.chip}>Showing {proposals.length} proposals</span>
          )}
        </div>
      </header>

      <section className={styles.controlsPanel}>
        <div className={styles.controlGroup}>
          <label htmlFor="trade-center-league">League</label>
          {loadingLeagues ? (
            <LoadingSpinner />
          ) : (
            <select
              id="trade-center-league"
              value={selectedLeagueKey}
              onChange={handleLeagueChange}
            >
              <option value="">Select your league…</option>
              {leagues.map((league) => (
                <option key={league.league_key} value={league.league_key}>
                  {league.league_name || league.league_key}
                </option>
              ))}
            </select>
          )}
          {leagueError && <div className={styles.errorText}>{leagueError}</div>}
        </div>

        <div className={styles.controlGroup}>
          <label>Target teams</label>
          {loadingTeams ? (
            <LoadingSpinner />
          ) : (
            <div className={styles.targetList}>
              {availableTargets.length === 0 && (
                <span className={styles.mutedText}>Select a league to choose target teams.</span>
              )}
              {availableTargets.map((team) => {
                const checked = selectedTargetKeys.includes(team.team_key);
                return (
                  <label key={team.team_key} className={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleTargetToggle(team.team_key)}
                    />
                    <span>{team.name || team.team_key}</span>
                  </label>
                );
              })}
            </div>
          )}
          {availableTargets.length > 0 && (
            <div className={styles.targetActions}>
              <button type="button" onClick={handleSelectAllTargets} className={styles.linkButton}>Select all</button>
              <button type="button" onClick={handleClearTargets} className={styles.linkButton}>Clear</button>
            </div>
          )}
        </div>

        <div className={styles.controlGroup}>
          <label htmlFor="horizon-range">Horizon focus</label>
          <input
            id="horizon-range"
            type="range"
            min="0"
            max="100"
            value={horizonFocus}
            onChange={(event) => setHorizonFocus(Number(event.target.value))}
          />
          <div className={styles.rangeLabels}>
            <span>Short term</span>
            <strong>{horizonFocus >= 50 ? 'Balanced' : horizonFocus <= 10 ? 'Immediate' : 'Near term'}</strong>
            <span>Rest of season</span>
          </div>
        </div>

        <div className={styles.controlGroup}>
          <label htmlFor="acceptance-range">Minimum acceptance probability</label>
          <input
            id="acceptance-range"
            type="range"
            min="0"
            max="0.5"
            step="0.01"
            value={minAcceptance}
            onChange={(event) => setMinAcceptance(Number(event.target.value))}
          />
          <div className={styles.rangeLabels}>
            <span>Flexible</span>
            <strong>{formatPercent(minAcceptance)}</strong>
            <span>Conservative</span>
          </div>
        </div>

        <div className={styles.controlGroup}>
          <label>Package size</label>
          <select value={maxPackageSize} onChange={(event) => setMaxPackageSize(Number(event.target.value))}>
            <option value={1}>1-for-1 only</option>
            <option value={2}>Include 2-player packages</option>
          </select>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={benchFirst}
              onChange={(event) => setBenchFirst(event.target.checked)}
            />
            <span>Prioritize opponent bench assets</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={includeInjured}
              onChange={(event) => setIncludeInjured(event.target.checked)}
            />
            <span>Allow injured players in proposals</span>
          </label>
        </div>

        <div className={styles.controlGroup}>
          <label htmlFor="topk-select">Number of proposals</label>
          <select id="topk-select" value={topK} onChange={(event) => setTopK(Number(event.target.value))}>
            <option value={6}>Top 6</option>
            <option value={12}>Top 12</option>
            <option value={20}>Top 20</option>
          </select>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={debugMode}
              onChange={(event) => setDebugMode(event.target.checked)}
            />
            <span>Include debug metadata</span>
          </label>
          <div className={styles.buttonRow}>
            <button type="button" className={styles.secondaryButton} onClick={resetFilters}>Reset filters</button>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={handleGenerate}
              disabled={isGenerating || !selectedLeagueKey}
            >
              {isGenerating ? 'Generating…' : 'Generate trades'}
            </button>
          </div>
          {generateError && <div className={styles.errorText}>{generateError}</div>}
        </div>
      </section>

      {(filteredOutCount > 0 || relaxedAcceptance) && (
        <div className={styles.filteredNotice}>
          {filteredOutCount > 0 && (
            <span>{filteredOutCount} proposal{filteredOutCount === 1 ? '' : 's'} hidden below {formatPercent(minAcceptance)} acceptance.</span>
          )}
          {relaxedAcceptance && (
            <span className={styles.filteredNoticeSecondary}>
              All remaining suggestions fall under the current threshold; showing best overall matches so you can review manually.
            </span>
          )}
        </div>
      )}

      {isGenerating && (
        <div className={styles.loadingPanel}>
          <LoadingSpinner />
          <span>Crunching the best packages…</span>
        </div>
      )}

      {!isGenerating && displayProposals.length === 0 && (
        <EmptyState
          title="No trade ideas yet"
          message={selectedLeagueKey ? 'Adjust your filters or broaden the target teams to discover more trades.' : 'Pick a league to start generating proposals.'}
        />
      )}

      {!isGenerating && displayProposals.length > 0 && (
        <section className={styles.proposalsSection}>
          {meta?.my_surplus_names?.length > 0 && (
            <div className={styles.surplusBox}>
              <strong>Top surplus assets:</strong> {meta.my_surplus_names.join(', ')}
            </div>
          )}

          <div className={styles.proposalsGrid}>
            {displayProposals.map((proposal) => {
              const tradeId = proposal.trade_id;
              const expanded = expandedTrades.includes(tradeId);
              const reasons = Array.isArray(proposal.reasons) ? proposal.reasons : [];
              const negotiationPitch = proposal.negotiation_pitch || '';
              const flags = proposal.flags || [];

              return (
                <article key={tradeId} className={styles.proposalCard}>
                  <header className={styles.proposalHeader}>
                    <div>
                      <h2>{tradeId.replace(/-/g, ' → ')}</h2>
                      <div className={styles.flagRow}>
                        <span className={`${styles.metric} ${styles.metricPositive}`}>My Δ {proposal.my_delta_points?.toFixed?.(1) ?? proposal.my_delta_points}</span>
                        <span className={`${styles.metric} ${Number(proposal.their_delta_points) >= 0 ? styles.metricPositive : styles.metricNegative}`}>
                          Their Δ {proposal.their_delta_points?.toFixed?.(1) ?? proposal.their_delta_points}
                        </span>
                        <span className={styles.metric}>Parity {proposal.value_parity_pct ?? '—'}%</span>
                        <span className={styles.metric}>Acceptance {formatPercent(proposal.acceptance_prob)}</span>
                        {proposal.ai_confidence && (
                          <span className={styles.chip}>AI confidence: {proposal.ai_confidence}</span>
                        )}
                        {flags.map((flag) => (
                          <span key={flag} className={`${styles.chip} ${styles.chipMuted}`}>{flag.replace('_', ' ')}</span>
                        ))}
                      </div>
                    </div>
                    <button
                      type="button"
                      className={styles.linkButton}
                      onClick={() => toggleDebugDetails(tradeId)}
                    >
                      {expanded ? 'Hide details' : 'View details'}
                    </button>
                  </header>

                  <div className={styles.playerColumns}>
                    <div className={styles.playerColumn}>
                      <h3>We send</h3>
                      <ul>
                        {(proposal.my_side || []).map((name) => (
                          <li key={name}>
                            <a href={toDossierLink(name)} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                              {name}
                            </a>
                          </li>
                        ))}
                        {proposal.suggested_drop && (
                          <li className={styles.dropSuggestion}>Drop: {proposal.suggested_drop}</li>
                        )}
                      </ul>
                    </div>
                    <div className={styles.playerColumn}>
                      <h3>They send</h3>
                      <ul>
                        {(proposal.their_side || []).map((name) => (
                          <li key={name}>
                            <a href={toDossierLink(name)} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                              {name}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className={styles.reasonSection}>
                    <h4>Why we like it</h4>
                    {reasons.length > 0 ? (
                      <ul>
                        {reasons.map((reason, index) => (
                          <li key={index}>{reason}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className={styles.mutedText}>AI explanations not available for this proposal.</p>
                    )}
                  </div>

                  <div className={styles.pitchSection}>
                    <h4>Negotiation pitch</h4>
                    {negotiationPitch ? (
                      <p>{negotiationPitch}</p>
                    ) : (
                      <p className={styles.mutedText}>Draft your own pitch to highlight how the trade helps your opponent.</p>
                    )}
                  </div>

                  {expanded && (
                    <div className={styles.debugSection}>
                      {debugLoading[tradeId] ? (
                        <div className={styles.loadingInline}>
                          <LoadingSpinner />
                          <span>Loading lineup impact…</span>
                        </div>
                      ) : debugData[tradeId]?.error ? (
                        <div className={styles.errorText}>{debugData[tradeId].error}</div>
                      ) : debugData[tradeId] ? (
                        <div className={styles.debugGrid}>
                          <div>
                            <h5>My lineup after trade</h5>
                            <ul>
                              {(debugData[tradeId].my_after_lineup || []).map((slot, index) => (
                                <li key={`${slot.slot}-${index}`}>
                                  <strong>{slot.slot}:</strong>{' '}
                                  {slot.name ? (
                                    <a href={toDossierLink(slot.name)} target="_blank" rel="noopener noreferrer">{slot.name}</a>
                                  ) : '—'}
                                  {slot.weekly_points !== undefined && ` (${slot.weekly_points?.toFixed?.(1) ?? slot.weekly_points} pts)`}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h5>Their lineup after trade</h5>
                            <ul>
                              {(debugData[tradeId].their_after_lineup || []).map((slot, index) => (
                                <li key={`${slot.slot}-${index}`}>
                                  <strong>{slot.slot}:</strong>{' '}
                                  {slot.name ? (
                                    <a href={toDossierLink(slot.name)} target="_blank" rel="noopener noreferrer">{slot.name}</a>
                                  ) : '—'}
                                  {slot.weekly_points !== undefined && ` (${slot.weekly_points?.toFixed?.(1) ?? slot.weekly_points} pts)`}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      ) : (
                        <p className={styles.mutedText}>No additional debug details available.</p>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
};

export default TradeCenter;
