# Frontend "My Team" Component Implementation Plan

## Overview
Implement Phase 1.2 - Frontend "My Team" component that displays Yahoo Fantasy Football rosters with integrated AI analysis, following established architecture patterns.

## Architecture Analysis

### Existing Patterns Identified
- **Components**: Functional React components in `/src/components/` with `.module.css` files
- **State Management**: Context API via AppContext.js, hooks for local state
- **API Integration**: Custom useApi hook with `get()` method, Bearer token auth
- **Routing**: Hash-based navigation (`#my-team`), activeTool state management
- **Styling**: CSS Modules with comprehensive theming (dark/light), CSS variables
- **Token Management**: localStorage with JSON token objects, auto-cleanup on errors

### Reference Components for Patterns
- **YahooLeagues.js**: OAuth token handling, API integration, error states
- **DraftCard.js**: Player data display, ECR integration, theming
- **Sidebar.js**: Navigation patterns, conditional display

## Implementation Plan

### Phase 1: Core Component Structure (30 min)

#### 1.1 Create MyTeam.js Component
**Location**: `/frontend/src/components/MyTeam.js`

**Core Structure**:
```javascript
import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import DraftCard from './DraftCard';
import LoadingSpinner from './LoadingSpinner';
import EmptyState from './EmptyState';
import styles from './MyTeam.module.css';

const MyTeam = () => {
    // State management following YahooLeagues pattern
    const [leagues, setLeagues] = useState([]);
    const [selectedLeague, setSelectedLeague] = useState(null);
    const [roster, setRoster] = useState([]);
    const [loading, setLoading] = useState(true);
    const [rosterLoading, setRosterLoading] = useState(false);
    const [error, setError] = useState(null);
    const { get } = useApi();

    // Token handling identical to YahooLeagues
    // League fetching on mount
    // Roster fetching on league selection
    // Error handling with token cleanup
};
```

**Key Features**:
- OAuth token management (localStorage + URL hash)
- League dropdown population
- Roster fetching with team_key
- Loading states for both leagues and roster
- Error handling with token expiration detection
- Empty state handling (pre-draft scenario)

#### 1.2 Token & Authentication Logic
**Pattern from YahooLeagues.js**:
```javascript
useEffect(() => {
    const initializeAndFetch = async () => {
        let tokenObject = null;
        
        // Step 1: Check URL hash for token
        const hash = window.location.hash;
        const tokenParam = new URLSearchParams(hash.split('?')[1]).get('token');
        
        if (tokenParam) {
            // Parse and store token, clean URL
        } else {
            // Load from localStorage
        }
        
        // Step 2: Fetch leagues with token
        if (tokenObject) {
            const authHeader = `Bearer ${tokenObject.access_token}`;
            const response = await get('/yahoo/leagues', {
                headers: { 'Authorization': authHeader }
            });
            // Handle response
        }
    };
    
    initializeAndFetch();
}, [get]);
```

#### 1.3 League Selection & Roster Fetching
```javascript
const handleLeagueSelect = useCallback(async (league) => {
    setSelectedLeague(league);
    setRosterLoading(true);
    setError(null);
    
    try {
        const tokenObject = JSON.parse(localStorage.getItem('yahoo_token'));
        const authHeader = `Bearer ${tokenObject.access_token}`;
        
        const rosterData = await get(`/yahoo/roster?team_key=${league.team_key}`, {
            headers: { 'Authorization': authHeader }
        });
        
        setRoster(rosterData);
    } catch (err) {
        // Handle 401 token expiration
        if (err.response?.status === 401) {
            setError('Token expired. Please log in again.');
            localStorage.removeItem('yahoo_token');
        } else {
            setError(err.message);
        }
    } finally {
        setRosterLoading(false);
    }
}, [get]);
```

### Phase 2: Component Integration (20 min)

#### 2.1 App.js Integration
**Add to imports**:
```javascript
import MyTeam from './components/MyTeam';
```

**Add route handling** (around line 518):
```javascript
if (hash === 'my-team') {
    setActiveTool('my-team');
}
```

**Add conditional rendering** (around line 751):
```javascript
{activeTool === 'my-team' && (
    <MyTeam />
)}
```

#### 2.2 Sidebar.js Integration
**Add conditional "My Team" link**:
```javascript
// After Target List (line 26), add:
{localStorage.getItem('yahoo_token') && (
    <li>
        <a href="#my-team" className={activeTool === 'my-team' ? 'active' : ''}>
            My Team
        </a>
    </li>
)}
```

**Alternative**: Add to Team Management section for better organization.

### Phase 3: Styling Implementation (15 min)

#### 3.1 Create MyTeam.module.css
**Location**: `/frontend/src/components/MyTeam.module.css`

**Following established patterns**:
```css
.container {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

.header {
    margin-bottom: 30px;
}

.leagueSelector {
    margin-bottom: 30px;
    padding: 20px;
    background-color: var(--card-background);
    border-radius: 8px;
    border: 1px solid var(--border-color);
}

.dropdown {
    width: 100%;
    max-width: 400px;
    padding: 12px;
    border: 1px solid var(--input-border);
    border-radius: 4px;
    background-color: var(--input-background);
    color: var(--text-color);
    font-size: 1em;
}

.rosterGrid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.emptyRoster {
    text-align: center;
    padding: 60px 20px;
    background-color: var(--card-background);
    border-radius: 8px;
    border: 1px solid var(--border-color);
    color: var(--text-muted);
}

.loading, .error {
    text-align: center;
    padding: 40px;
    font-size: 1.2em;
}

.error {
    color: var(--danger-color);
    background-color: var(--card-background);
    border-radius: 8px;
    border: 1px solid var(--danger-color);
}

/* Responsive design */
@media (max-width: 768px) {
    .rosterGrid {
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .container {
        padding: 15px;
    }
}
```

### Phase 4: Player Display Integration (15 min)

#### 4.1 Roster Player Component
**Reuse DraftCard for consistency**:
```javascript
const RosterPlayer = ({ player, index }) => {
    return (
        <div className={styles.playerCard}>
            <div className={styles.playerHeader}>
                <h3>{player.name}</h3>
                <span className={styles.position}>{player.selected_position}</span>
            </div>
            
            <div className={styles.playerStats}>
                <div className={styles.statRow}>
                    <span>Team:</span>
                    <span>{player.team}</span>
                </div>
                <div className={styles.statRow}>
                    <span>ECR Overall:</span>
                    <span>{player.ecr_overall?.toFixed(1) || 'N/A'}</span>
                </div>
                <div className={styles.statRow}>
                    <span>Bye Week:</span>
                    <span>{player.bye_week || 'N/A'}</span>
                </div>
            </div>
        </div>
    );
};
```

#### 4.2 Empty State Handling
```javascript
// For pre-draft scenario
if (roster.length === 0) {
    return (
        <div className={styles.emptyRoster}>
            <h3>No Players Drafted Yet</h3>
            <p>Your roster will appear here after your draft.</p>
            <p>Draft Status: Pre-Draft</p>
        </div>
    );
}
```

### Phase 5: Error Handling & Edge Cases (10 min)

#### 5.1 Comprehensive Error States
- **No token**: "Please log in with Yahoo to view your teams"
- **Token expired**: "Session expired. Please log in again" + localStorage cleanup
- **No leagues**: "No fantasy football leagues found"
- **Empty roster**: "No players drafted yet" (expected pre-draft)
- **API errors**: Display error message with retry option

#### 5.2 Loading States
- **Initial load**: Full page spinner while fetching leagues
- **League selection**: Roster area spinner while fetching roster
- **Skeleton loading**: Consider skeleton placeholders for better UX

### Phase 6: Testing Scenarios (15 min)

#### 6.1 Pre-Draft Testing (Current State)
- ✅ Leagues load correctly
- ✅ Dropdown populated with league names
- ✅ Empty roster displays appropriate message
- ✅ No errors or crashes with empty roster

#### 6.2 Post-Draft Testing (Future)
- [ ] Roster loads with actual player data
- [ ] Player cards display enriched data (ECR, bye weeks, AI analysis)
- [ ] Responsive design works on mobile
- [ ] Token expiration handled gracefully

#### 6.3 Error Scenarios
- [ ] Invalid token handling
- [ ] Network failures
- [ ] Missing league data
- [ ] Backend API errors

## Implementation Checklist

### Core Implementation
- [ ] Create MyTeam.js component with OAuth token handling
- [ ] Implement league dropdown with /api/yahoo/leagues integration
- [ ] Add roster fetching with /api/yahoo/roster integration
- [ ] Create MyTeam.module.css with responsive design
- [ ] Add route handling in App.js
- [ ] Add conditional sidebar link in Sidebar.js

### Integration & Polish
- [ ] Reuse DraftCard patterns for player display
- [ ] Implement loading states and error handling
- [ ] Add empty state for pre-draft scenario
- [ ] Test responsive design on mobile
- [ ] Verify token expiration handling
- [ ] Add proper TypeScript types (if applicable)

### Testing & Validation
- [ ] Test with current empty roster state
- [ ] Verify league selection functionality
- [ ] Test error states and recovery
- [ ] Validate responsive design
- [ ] Prepare for post-draft testing

## Technical Notes

### Token Management
- Use identical pattern from YahooLeagues.js
- Store full token object in localStorage as 'yahoo_token'
- Parse access_token for Bearer auth header
- Clean up on 401 errors

### API Integration
- Use existing useApi hook with get() method
- Follow established error handling patterns
- Implement proper loading states
- Handle empty responses gracefully

### Component Architecture
- Follow functional component + hooks pattern
- Use CSS Modules for styling consistency
- Integrate with existing Context API if needed
- Maintain responsive design principles

### Future Enhancements
- Week parameter support for historical rosters
- Player detail modals
- Roster comparison between leagues
- AI analysis integration for roster optimization

## Estimated Timeline
- **Phase 1-2**: 50 minutes (Core component + integration)
- **Phase 3-4**: 30 minutes (Styling + player display)
- **Phase 5-6**: 25 minutes (Error handling + testing)
- **Total**: ~2 hours for complete implementation

## Dependencies
- ✅ Backend APIs functional (/api/yahoo/leagues, /api/yahoo/roster)
- ✅ OAuth token management working
- ✅ Existing component patterns established
- ✅ CSS theming system in place
- ✅ DraftCard component available for reuse

This implementation plan provides step-by-step guidance for creating a production-ready "My Team" component that seamlessly integrates with the existing RATM Draft Kit architecture.