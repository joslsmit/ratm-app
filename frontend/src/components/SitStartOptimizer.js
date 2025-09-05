import React, { useEffect, useState, useContext } from 'react';
import { useApi } from '../hooks/useApi';
import { AppContext } from '../context/AppContext';

export default function SitStartOptimizer() {
  const { get } = useApi();
  const { API_BASE_URL } = useContext(AppContext);
  const [isYahooUser, setIsYahooUser] = useState(false);
  const [leagues, setLeagues] = useState([]);
  const [leagueKey, setLeagueKey] = useState('');
  const [teamKey, setTeamKey] = useState('');
  const [week, setWeek] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('yahoo_token');
    if (token) {
      setIsYahooUser(true);
      // Fetch leagues
      try {
        const tokenObj = JSON.parse(token);
        const auth = `Bearer ${tokenObj.access_token}`;
        (async () => {
          try {
            const ls = await get('/yahoo/leagues', { headers: { Authorization: auth }});
            setLeagues(ls || []);
            if (ls && ls.length === 1) {
              setLeagueKey(ls[0].league_key);
              setTeamKey(ls[0].team_key);
            }
          } catch (e) {
            setError('Unable to load Yahoo leagues. Please re‑authenticate.');
          }
        })();
      } catch (_) {}
    }
  }, [get]);

  const optimize = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const tokenObj = JSON.parse(localStorage.getItem('yahoo_token') || '{}');
      const auth = `Bearer ${tokenObj.access_token}`;
      const body = { mode: 'yahoo', team_key: teamKey, league_key: leagueKey || undefined, week: week || undefined };
      const rsp = await fetch(`${API_BASE_URL}/optimize_lineup`, { method: 'POST', headers: { 'Authorization': auth, 'Content-Type': 'application/json', 'X-API-Key': localStorage.getItem('geminiApiKey') || '' }, body: JSON.stringify(body) });
      if (!rsp.ok) { const e = await rsp.json().catch(()=>({})); throw new Error(e.error || `HTTP ${rsp.status}`); }
      const data = await rsp.json();
      setResult(data);
    } catch (e) {
      setError(e.message || 'Optimization failed');
    } finally { setLoading(false); }
  };

  if (!isYahooUser) {
    return (
      <section className="tool-section">
        <h2>Sit/Start Optimizer</h2>
        <p>Sign in with Yahoo (sidebar) to optimize your actual lineup.</p>
      </section>
    );
  }

  return (
    <section className="tool-section">
      <h2>Sit/Start Optimizer</h2>
      <div className="card">
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label>League:&nbsp;</label>
            <select value={leagueKey} onChange={(e)=>{ setLeagueKey(e.target.value); const l = leagues.find(x=>x.league_key===e.target.value); setTeamKey(l?.team_key||''); }}>
              <option value="">Select a league…</option>
              {leagues.map(l => <option key={l.league_key} value={l.league_key}>{l.league_name}</option>)}
            </select>
          </div>
          <div>
            <label>Week:&nbsp;</label>
            <input type="number" min="1" max="18" value={week} onChange={(e)=>setWeek(e.target.value)} style={{ width: 80 }} />
          </div>
          <button onClick={optimize} disabled={loading || !teamKey}>{loading ? 'Optimizing…' : 'Optimize My Lineup'}</button>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      {result && (
        <div className="card">
          <h3>Suggested Lineup</h3>
          <div>
            {Object.entries(result.suggested_lineup || {}).map(([slot, name]) => {
              const href = name ? `/?tool=dossier&player=${encodeURIComponent(name)}` : null;
              return (
                <div key={slot}>
                  <strong>{slot}:</strong> {name ? <a href={href} target="_blank" rel="noopener noreferrer">{name}</a> : '—'}
                </div>
              );
            })}
          </div>
          <h4 style={{ marginTop: 12 }}>Changes</h4>
          {(result.diff && result.diff.length) ? result.diff.map((d,i)=> {
            const fromHref = d.from ? `/?tool=dossier&player=${encodeURIComponent(d.from)}` : null;
            const toHref = d.to ? `/?tool=dossier&player=${encodeURIComponent(d.to)}` : null;
            return (
              <div key={i}>
                {d.slot}: {d.from ? <a href={fromHref} target="_blank" rel="noopener noreferrer">{d.from}</a> : '—'} → {d.to ? <a href={toHref} target="_blank" rel="noopener noreferrer">{d.to}</a> : '—'}
              </div>
            );
          }) : <div>No changes needed.</div>}
          <div style={{ marginTop: 12 }}><strong>Total Projected Points:</strong> {result.total_projected_points}</div>
          {result.eligibility_info && (
            <div style={{ marginTop: 12 }}>
              {result.eligibility_info.excluded?.length ? <div><strong>Excluded:</strong> {result.eligibility_info.excluded.join(', ')}</div> : null}
              {result.eligibility_info.flagged?.length ? <div><strong>Flagged (Q/D):</strong> {result.eligibility_info.flagged.join(', ')}</div> : null}
            </div>
          )}
          {result.ai_note_json && (
            <div style={{ marginTop: 12 }}>
              {/* Tags */}
              {Array.isArray(result.ai_note_json.tags) && result.ai_note_json.tags.length > 0 && (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                  {result.ai_note_json.tags.map((t, idx) => (
                    <span key={idx} style={{ padding: '2px 8px', background: 'var(--chip-bg, #eef1f5)', borderRadius: 12, fontSize: 12, border: '1px solid var(--chip-border, #cfd6e4)' }}>{t}</span>
                  ))}
                </div>
              )}
              {/* Score breakdown */}
              {result.ai_note_json.score_breakdown && (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12, fontSize: 13 }}>
                  {Object.entries(result.ai_note_json.score_breakdown).map(([k, v]) => (
                    <span key={k} style={{ padding: '2px 6px', background: '#f7f7f9', borderRadius: 6, border: '1px solid #e5e7eb' }}>
                      <strong style={{ textTransform: 'capitalize' }}>{k}:</strong> {Number(v) >= 0 ? '+' : ''}{Number(v).toFixed(2)}
                    </span>
                  ))}
                </div>
              )}
              {/* Structured reasons with type chips and clarified labels */}
              <div style={{ border: '1px solid var(--chip-border, #cfd6e4)', borderRadius: 8, padding: 12, background: 'var(--surface-subtle, #fafbfc)' }}>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>{result.ai_note_json.headline}</div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.ai_note_json.reasons || []).map((r, idx) => {
                    const t = (r.type || '').trim();
                    const ev = r.evidence || {};
                    // Map type to a concise chip label
                    let chip = t;
                    if (t === 'FlexAllocation') chip = 'Flex Fit';
                    if (t === 'Context' && ev.type === 'overall') chip = 'Overall ECR';
                    // Derive clearer matchup text when difficulties are present; parse names from headline
                    let text = r.text || '';
                    try {
                      const headline = result.ai_note_json.headline || '';
                      const m = headline.match(/^Start\s+(.+)\s+over\s+(.+)\s+at\s+/);
                      const toName = m && m[1] ? m[1] : '';
                      const fromName = m && m[2] ? m[2] : '';
                      const matchupNudge = (result.ai_note_json.score_breakdown && typeof result.ai_note_json.score_breakdown.matchup === 'number') ? result.ai_note_json.score_breakdown.matchup : 0;
                      if (t === 'Matchup' && ev.to_matchup_difficulty && ev.from_matchup_difficulty && toName && fromName) {
                        const label = matchupNudge < 0 ? 'Tougher matchup this week' : 'Easier matchup this week';
                        const nudgeStr = matchupNudge !== 0 ? ` [matchup ${matchupNudge > 0 ? '+' : ''}${matchupNudge.toFixed(2)}]` : '';
                        text = `${label}: ${toName} (${ev.to_matchup_difficulty}) vs ${fromName} (${ev.from_matchup_difficulty})${nudgeStr}.`;
                      }
                    } catch (e) { /* noop */ }
                    return (
                      <li key={idx} style={{ marginBottom: 6 }}>
                        <span style={{ padding: '1px 6px', marginRight: 8, background: '#eef1f5', borderRadius: 10, border: '1px solid #cfd6e4', fontSize: 11 }}>{chip}</span>
                        <span>{text}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          )}
          {/* Markdown note hidden; structured card above replaces it */}
          {/* Debug block if present */}
          {result.debug && result.debug.lineup_note && (
            <details style={{ marginTop: 12 }}>
              <summary>Debug: Lineup Note Details</summary>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(result.debug.lineup_note, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
