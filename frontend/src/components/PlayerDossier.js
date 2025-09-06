import React, { useState, useRef } from 'react';
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

  // === TOOLTIP COMPONENT ===
  const Tooltip = ({ children, content, detailed = false }) => {
    const [showTooltip, setShowTooltip] = useState(false);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const tooltipRef = useRef(null);
    
    const handleMouseEnter = (e) => {
      setPosition({ x: e.clientX, y: e.clientY });
      setShowTooltip(true);
    };
    
    const handleMouseLeave = () => {
      setShowTooltip(false);
    };
    
    return (
      <span 
        className={styles.tooltipWrapper}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
        {showTooltip && (
          <div 
            ref={tooltipRef}
            className={`${styles.tooltip} ${detailed ? styles.tooltipDetailed : ''}`}
            style={{
              position: 'fixed',
              left: `${position.x + 10}px`,
              top: `${position.y - 10}px`,
              zIndex: 1000,
              pointerEvents: 'none'
            }}
          >
            {typeof content === 'string' ? (
              <div dangerouslySetInnerHTML={{ __html: content }} />
            ) : (
              content
            )}
          </div>
        )}
      </span>
    );
  };

  // === DATA INTERPRETATION HELPER FUNCTIONS ===
  
  // Percentile and tier calculation utilities
  const calculatePercentile = (value, thresholds) => {
    if (!value) return null;
    
    if (value >= thresholds.elite) return { percentile: 95, tier: 'elite', label: 'Top 5%' };
    if (value >= thresholds.high) return { percentile: 75, tier: 'high', label: 'Top 25%' };
    if (value >= thresholds.good) return { percentile: 60, tier: 'good', label: 'Above Average' };
    if (value >= thresholds.standard) return { percentile: 40, tier: 'standard', label: 'Average' };
    return { percentile: 20, tier: 'limited', label: 'Below Average' };
  };

  const getPositionalValueThresholds = (position) => {
    // Value score thresholds by position
    const thresholds = {
      QB: { elite: 20, high: 15, good: 10, standard: 5 },
      RB: { elite: 18, high: 14, good: 10, standard: 6 },
      WR: { elite: 16, high: 12, good: 8, standard: 4 },
      TE: { elite: 15, high: 11, good: 7, standard: 3 }
    };
    return thresholds[position] || thresholds.RB;
  };

  const interpretValueScore = (valueScore, position) => {
    if (!valueScore) return null;
    
    const thresholds = getPositionalValueThresholds(position);
    const percentileInfo = calculatePercentile(valueScore, thresholds);
    
    if (valueScore >= thresholds.elite) {
      return {
        badge: '💎 Elite Value',
        description: 'Premium player - top tier value',
        tier: 'elite',
        context: `${percentileInfo.label} value for ${position}`,
        percentile: percentileInfo.percentile,
        scoreContext: `Draft Value Rating: ${valueScore} (Elite Tier)`,
        whyItMatters: 'This player delivers exceptional production relative to their draft cost - a cornerstone for championship teams',
        fantasyImpact: 'Target aggressively in drafts and trades. Players with elite value often become season-defining picks.',
        tone: 'confident-excitement'
      };
    } else if (valueScore >= thresholds.high) {
      return {
        badge: '⭐ High Value', 
        description: 'Above average value pick',
        tier: 'high',
        context: `${percentileInfo.label} value for ${position}`,
        percentile: percentileInfo.percentile,
        scoreContext: `Draft Value Rating: ${valueScore} (High Tier)`,
        whyItMatters: 'Strong production potential at this draft position creates roster flexibility and upside',
        fantasyImpact: 'Excellent draft targets that can outperform ADP. Great building blocks for competitive lineups.',
        tone: 'enthusiastic-positive'
      };
    } else if (valueScore >= thresholds.good) {
      return {
        badge: '✅ Good Value',
        description: 'Solid fantasy asset',
        tier: 'good', 
        context: `${percentileInfo.label} value for ${position}`,
        percentile: percentileInfo.percentile,
        scoreContext: `Draft Value Rating: ${valueScore} (Good Tier)`,
        whyItMatters: 'Reliable players who meet or exceed expectations at their current draft position',
        fantasyImpact: 'Safe, dependable options that provide good floor with some upside potential.',
        tone: 'confident-steady'
      };
    } else if (valueScore >= thresholds.standard) {
      return {
        badge: '📊 Standard Value',
        description: 'Fair market value',
        tier: 'standard',
        context: `${percentileInfo.label} value for ${position}`,
        percentile: percentileInfo.percentile,
        scoreContext: `Draft Value Rating: ${valueScore} (Standard Tier)`,
        whyItMatters: 'Players priced fairly by the market - production likely matches draft investment',
        fantasyImpact: 'Reasonable selections when better values are unavailable. Focus on upside factors.',
        tone: 'balanced-neutral'
      };
    } else {
      return {
        badge: '⚠️ Limited Value',
        description: 'Below replacement level',
        tier: 'limited',
        context: `${percentileInfo.label} value for ${position}`,
        percentile: percentileInfo.percentile,
        scoreContext: `Draft Value Rating: ${valueScore} (Limited Tier)`,
        whyItMatters: 'Current draft cost likely exceeds expected production - better options available',
        fantasyImpact: 'Avoid unless significant upside factors emerge. Look for better value elsewhere.',
        tone: 'cautious-advisory'
      };
    }
  };

  const interpretOpportunityScore = (opportunityScore, ownership) => {
    if (!opportunityScore) return null;
    
    const thresholds = { elite: 25, high: 20, good: 15, standard: 10 };
    const percentileInfo = calculatePercentile(opportunityScore, thresholds);
    
    if (opportunityScore >= 25) {
      return {
        badge: '🚨 Must-Add Target',
        description: 'Exceptional value opportunity',
        tier: 'exceptional',
        context: `${percentileInfo.label} opportunity - Immediate waiver priority`,
        action: 'Add immediately if available',
        percentile: percentileInfo.percentile,
        scoreContext: `Waiver Priority Score: ${opportunityScore} (Exceptional)`,
        whyItMatters: 'Rare combination of low ownership and high projected production creates massive opportunity',
        fantasyImpact: 'Drop lower-tier players immediately. This could be a league-winning pickup.',
        urgency: 'Act NOW - other sharp managers will target this player quickly!'
      };
    } else if (opportunityScore >= 20) {
      return {
        badge: '🎯 High Priority Target', 
        description: 'Strong value opportunity',
        tier: 'high',
        context: `${percentileInfo.label} opportunity - Top waiver consideration`,
        action: 'Strong add candidate',
        percentile: percentileInfo.percentile,
        scoreContext: `Waiver Priority Score: ${opportunityScore} (High Priority)`,
        whyItMatters: 'Solid production potential with limited roster competition makes this a smart pickup',
        fantasyImpact: 'Use significant waiver priority or FAAB. Could provide immediate lineup upgrade.',
        urgency: 'Move quickly before ownership increases!'
      };
    } else if (opportunityScore >= 15) {
      return {
        badge: '📈 Good Opportunity',
        description: 'Above average value available',
        tier: 'good',
        context: `${percentileInfo.label} opportunity - Worth monitoring closely`,
        action: 'Consider adding',
        percentile: percentileInfo.percentile,
        scoreContext: `Waiver Priority Score: ${opportunityScore} (Good Value)`,
        whyItMatters: 'Decent upside potential with reasonable availability creates a solid opportunity',
        fantasyImpact: 'Good depth addition or streaming option. Monitor for increased role or usage.',
        urgency: 'Add if you have bench space or specific positional need.'
      };
    } else if (opportunityScore >= 10) {
      return {
        badge: '📊 Standard Opportunity',
        description: 'Fair market value',
        tier: 'standard', 
        context: `${percentileInfo.label} opportunity - Limited upside available`,
        action: 'Standard consideration',
        percentile: percentileInfo.percentile,
        scoreContext: `Waiver Priority Score: ${opportunityScore} (Standard)`,
        whyItMatters: 'Market has fairly priced this player - limited edge available for savvy managers',
        fantasyImpact: 'Reasonable depth option but no significant advantage. Focus on other priorities.',
        urgency: 'No rush - evaluate based on specific roster needs only.'
      };
    } else {
      return {
        badge: '⚪ Limited Opportunity',
        description: 'Market fairly valued',
        tier: 'limited',
        context: `${percentileInfo.label} opportunity - No significant value edge`,
        action: 'Look for better options',
        percentile: percentileInfo.percentile,
        scoreContext: `Waiver Priority Score: ${opportunityScore} (Limited)`,
        whyItMatters: 'High ownership or low projection limits upside potential for waiver wire managers',
        fantasyImpact: 'Avoid using resources here. Better opportunities exist elsewhere.',
        urgency: 'Skip this player and focus on higher-value targets instead.'
      };
    }
  };

  const interpretOwnership = (ownership, projection) => {
    if (ownership === null || ownership === undefined) return null;
    
    let context = '';
    let tier = '';
    let opportunity = '';
    let percentileLabel = '';
    
    if (ownership < 10) {
      tier = 'ultra-low';
      context = 'Hidden from most managers';
      opportunity = projection >= 15 ? 'Massive upside potential' : 'Deep sleeper candidate';
      percentileLabel = 'Bottom 10% ownership';
    } else if (ownership < 25) {
      tier = 'low';  
      context = 'Under the radar';
      opportunity = projection >= 12 ? 'Strong value opportunity' : 'Speculative add';
      percentileLabel = 'Bottom 25% ownership';
    } else if (ownership < 50) {
      tier = 'moderate';
      context = 'Some manager interest'; 
      opportunity = projection >= 15 ? 'Good value available' : 'Moderate opportunity';
      percentileLabel = 'Below average ownership';
    } else if (ownership < 75) {
      tier = 'high';
      context = 'Popular choice';
      opportunity = 'Limited upside remaining';
      percentileLabel = 'Above average ownership';
    } else if (ownership < 90) {
      tier = 'very-high';
      context = 'Widely recognized';
      opportunity = 'Consensus pick - minimal edge';
      percentileLabel = 'Top 25% ownership';
    } else {
      tier = 'universal';
      context = 'Must-own player';
      opportunity = 'No availability upside';
      percentileLabel = 'Top 10% ownership';
    }
    
    return {
      percentage: ownership,
      tier,
      context: `${context} (${percentileLabel})`,
      opportunity,
      badge: ownership < 25 ? '💎' : ownership < 50 ? '📈' : ownership < 75 ? '📊' : '🔥',
      percentileContext: percentileLabel,
      availabilityContext: ownership < 50 ? 'Likely available on waivers' : ownership < 80 ? 'May be available in some leagues' : 'Rarely available - likely rostered',
      whyItMatters: ownership < 25 ? 'Low ownership creates massive advantage if player delivers - few managers competing for his production' : 
                    ownership < 50 ? 'Moderate ownership suggests some manager recognition but still room for advantage' :
                    ownership < 75 ? 'High ownership indicates widespread recognition - limited competitive edge remaining' :
                    'Universal ownership means everyone already has this player - no acquisition advantage possible',
      fantasyImpact: ownership < 25 ? 'Perfect waiver wire or trade target - huge upside if you secure him while others sleep' :
                     ownership < 50 ? 'Good pickup opportunity - can provide edge over managers who missed this player' :
                     ownership < 75 ? 'Standard roster option - most experienced managers already rostered' :
                     'Must-own consensus pick - likely unavailable but universally recognized value',
      competitiveEdge: ownership < 25 ? 'HIGH - Major advantage over field' : 
                       ownership < 50 ? 'MODERATE - Some advantage available' :
                       ownership < 75 ? 'LOW - Limited edge remaining' :
                       'NONE - No advantage possible'
    };
  };

  const interpretProjection = (projection, position, grade) => {
    if (!projection) return null;
    
    let tier = '';
    let context = '';
    let confidence = '';
    let percentileContext = '';
    
    const getProjectionPercentile = (points, pos) => {
      const thresholds = {
        QB: { elite: 25, excellent: 22, solid: 18, serviceable: 15 },
        RB: { elite: 20, excellent: 16, solid: 12, flex: 8 },
        WR: { elite: 18, excellent: 15, solid: 12, flex: 8 },
        TE: { elite: 15, excellent: 12, solid: 8, limited: 5 }
      };
      
      const posThresholds = thresholds[pos] || thresholds.RB;
      
      if (points >= posThresholds.elite) return 'Top 5% weekly ceiling';
      if (points >= posThresholds.excellent) return 'Top 15% weekly performance';
      if (points >= posThresholds.solid) return 'Above average weekly output';
      if (points >= (posThresholds.flex || posThresholds.serviceable || 10)) return 'Average weekly production';
      return 'Below average weekly expectation';
    };
    
    percentileContext = getProjectionPercentile(projection, position);
    
    if (position === 'QB') {
      if (projection >= 25) {
        tier = 'elite';
        context = 'Elite QB1 performance expected';
        confidence = 'Very high ceiling week';
      } else if (projection >= 22) {
        tier = 'excellent';
        context = 'Strong QB1 production likely';
        confidence = 'High ceiling week';
      } else if (projection >= 18) {
        tier = 'solid';
        context = 'Reliable QB2 performance';
        confidence = 'Safe floor with upside';
      } else if (projection >= 15) {
        tier = 'serviceable';
        context = 'Streaming-viable performance';
        confidence = 'Modest expectations';
      } else {
        tier = 'concerning';
        context = 'Below-average QB production';
        confidence = 'Risky play';
      }
    } else if (position === 'RB') {
      if (projection >= 20) {
        tier = 'elite';
        context = 'RB1 ceiling performance';
        confidence = 'Top-tier weekly play';
      } else if (projection >= 16) {
        tier = 'excellent'; 
        context = 'Strong RB1/2 production';
        confidence = 'Confident weekly start';
      } else if (projection >= 12) {
        tier = 'solid';
        context = 'Reliable RB2/Flex option';
        confidence = 'Safe weekly choice';
      } else if (projection >= 8) {
        tier = 'flex';
        context = 'Flex-worthy with TD upside';
        confidence = 'Boom-or-bust potential';
      } else {
        tier = 'limited';
        context = 'Limited scoring ceiling';
        confidence = 'Touchdown dependent';
      }
    } else if (position === 'WR') {
      if (projection >= 18) {
        tier = 'elite';
        context = 'WR1 ceiling performance';
        confidence = 'Must-start weekly option';
      } else if (projection >= 15) {
        tier = 'excellent';
        context = 'Strong WR1/2 production';  
        confidence = 'Confident weekly start';
      } else if (projection >= 12) {
        tier = 'solid';
        context = 'Reliable WR2/Flex option';
        confidence = 'Solid weekly choice';
      } else if (projection >= 8) {
        tier = 'flex';
        context = 'Flex consideration';
        confidence = 'Moderate upside play';
      } else {
        tier = 'limited';
        context = 'Limited weekly ceiling';
        confidence = 'Deep league consideration';
      }
    } else if (position === 'TE') {
      if (projection >= 15) {
        tier = 'elite';
        context = 'Elite TE1 performance';
        confidence = 'Positional advantage week';
      } else if (projection >= 12) {
        tier = 'excellent';
        context = 'Strong TE1 production';
        confidence = 'Reliable weekly starter';
      } else if (projection >= 8) {
        tier = 'solid';
        context = 'Streaming-viable performance';
        confidence = 'Decent weekly option';
      } else {
        tier = 'limited'; 
        context = 'Limited scoring potential';
        confidence = 'Touchdown dependent';
      }
    }
    
    return {
      points: projection,
      tier,
      context: `${context} (${percentileContext})`,
      confidence,
      grade: grade || null,
      badge: tier === 'elite' ? '🚀' : tier === 'excellent' ? '⭐' : tier === 'solid' ? '✅' : tier === 'flex' ? '📊' : '⚠️',
      percentileContext,
      weeklyRank: `${projection} pts - ${percentileContext}`,
      whyItMatters: tier === 'elite' ? 'Elite weekly projection indicates high ceiling week - perfect for tournament play and must-start lineups' :
                    tier === 'excellent' ? 'Strong projection suggests reliable points with upside - confident weekly starter' :
                    tier === 'solid' ? 'Solid projection provides good floor with decent upside - safe weekly option' :
                    tier === 'flex' || tier === 'serviceable' ? 'Moderate projection offers streaming value or flex consideration' :
                    'Low projection suggests challenging week - consider alternatives if available',
      startSitGuidance: tier === 'elite' ? 'MUST START - Elite ceiling week, perfect for all formats' :
                        tier === 'excellent' ? 'STRONG START - High confidence, great for cash games' :
                        tier === 'solid' ? 'SAFE START - Reliable floor, good for conservative lineups' :
                        tier === 'flex' || tier === 'serviceable' ? 'FLEX CONSIDERATION - Monitor matchup factors' :
                        'CONSIDER BENCHING - Look for better options if available',
      weeklyStrategy: tier === 'elite' ? 'Target in DFS tournaments, stack with teammates, build lineups around this performance' :
                      tier === 'excellent' ? 'Strong cash game play, reliable tournament option, pair with safe floor players' :
                      tier === 'solid' ? 'Solid foundation player, good for balanced lineups, reasonable ceiling/floor' :
                      'Monitor snap counts, target share, and game script before finalizing decision'
    };
  };

  const interpretAgeTrajectory = (age, ageCategory, position) => {
    if (!age && !ageCategory) return null;
    
    let trajectory = '';
    let outlook = '';
    let strategy = '';
    let urgency = '';
    let ageContext = '';
    
    // Position-specific age context
    const getAgeContext = (playerAge, pos) => {
      const ageRanges = {
        QB: { young: 26, prime: 32, veteran: 37 },
        RB: { young: 24, prime: 28, veteran: 30 },
        WR: { young: 25, prime: 29, veteran: 32 },
        TE: { young: 25, prime: 30, veteran: 33 }
      };
      
      const ranges = ageRanges[pos] || ageRanges.RB;
      
      if (playerAge <= ranges.young) return `Young for ${pos} (Bottom 25% age)`;
      if (playerAge <= ranges.prime) return `Prime age for ${pos} (Optimal window)`;
      if (playerAge <= ranges.veteran) return `Veteran age for ${pos} (Experience phase)`;
      return `Late career for ${pos} (Top 10% age)`;
    };
    
    if (age) {
      ageContext = getAgeContext(age, position);
    }
    
    if (ageCategory?.includes('Prime') || ageCategory?.includes('Peak')) {
      trajectory = 'Peak Performance Window';
      outlook = 'Optimal fantasy production expected';
      strategy = position === 'RB' ? 'Maximize value now' : 'Core roster piece';
      urgency = 'high-value';
    } else if (ageCategory?.includes('Ascending') || ageCategory?.includes('Development')) {
      trajectory = 'Rising Trajectory';
      outlook = 'Upside potential ahead';
      strategy = 'Dynasty buy target - growth ahead';
      urgency = 'growth-potential';
    } else if (ageCategory?.includes('Decline') || ageCategory?.includes('Risk')) {
      trajectory = 'Decline Risk';
      outlook = position === 'RB' ? 'Age cliff concerns' : 'Monitor closely';
      strategy = 'Consider selling in dynasty';
      urgency = 'decline-risk';
    } else {
      trajectory = 'Standard Trajectory';
      outlook = 'Normal age-related expectations';
      strategy = 'Standard roster consideration';
      urgency = 'standard';
    }
    
    return {
      age,
      trajectory: `${trajectory} (${ageContext})`,
      outlook, 
      strategy,
      urgency,
      badge: urgency === 'growth-potential' ? '📈' : urgency === 'high-value' ? '🎯' : urgency === 'decline-risk' ? '⏰' : '📊',
      ageContext,
      careerPhase: age <= (position === 'RB' ? 24 : 26) ? 'Early Career' : 
                   age <= (position === 'RB' ? 28 : position === 'QB' ? 32 : 29) ? 'Prime Years' : 
                   'Veteran Stage',
      whyItMatters: urgency === 'growth-potential' ? 'Young players entering their prime often see dramatic production increases - perfect dynasty targets' :
                    urgency === 'high-value' ? 'Players in their peak years deliver maximum production - the sweet spot for championship runs' :
                    urgency === 'decline-risk' ? 'Age-related decline risk increases significantly - important for roster planning and trade timing' :
                    'Standard aging curve expectations - no major age-related advantages or concerns',
      rosterStrategy: urgency === 'growth-potential' ? 'BUY AGGRESSIVELY in dynasty, target in redraft for breakout potential' :
                      urgency === 'high-value' ? 'CORNERSTONE PLAYER - build your team around these prime years' :
                      urgency === 'decline-risk' ? 'SELL HIGH in dynasty, use carefully in redraft with exit strategy' :
                      'STANDARD APPROACH - age is not a significant factor in valuation',
      timelineGuidance: urgency === 'growth-potential' ? 'Multi-year upside trajectory - patience rewarded with growth' :
                        urgency === 'high-value' ? 'Win-now window - maximize value in current season' :
                        urgency === 'decline-risk' ? 'Limited window - act quickly before production drops' :
                        'Standard timeline - normal career progression expected'
    };
  };

  const interpretMatchup = (opponent, difficulty, homeAway) => {
    if (!opponent && !difficulty) return null;
    
    let assessment = '';
    let context = '';
    let recommendation = '';
    let confidence = '';
    let difficultyContext = '';
    
    // Matchup difficulty percentile context
    const getMatchupContext = (diff) => {
      if (diff === 'Easy') return 'Top 25% favorable matchups';
      if (diff === 'Tough') return 'Bottom 25% difficult matchups';
      if (diff === 'Moderate') return 'Average matchup difficulty';
      return 'Standard matchup expectations';
    };
    
    difficultyContext = getMatchupContext(difficulty);
    
    if (difficulty === 'Easy') {
      assessment = 'Favorable Matchup';
      context = `Exploit this opportunity (${difficultyContext})`;
      recommendation = 'Start with confidence';
      confidence = 'high';
    } else if (difficulty === 'Tough') { 
      assessment = 'Challenging Matchup';
      context = `Reduced ceiling likely (${difficultyContext})`;
      recommendation = 'Proceed with caution';
      confidence = 'low';
    } else if (difficulty === 'Moderate') {
      assessment = 'Neutral Matchup';
      context = `Standard expectations (${difficultyContext})`;
      recommendation = 'Rely on talent level';
      confidence = 'moderate';
    } else {
      assessment = 'Standard Matchup';
      context = 'No significant matchup edge';
      recommendation = 'Normal expectations';
      confidence = 'moderate';
    }
    
    const locationContext = homeAway === 'Home' ? 'Home field advantage' : 
                          homeAway === 'Away' ? 'Road game considerations' : 
                          'Neutral site';
    
    return {
      opponent,
      assessment,
      context,
      recommendation,
      confidence,
      homeAway,
      locationContext,
      badge: difficulty === 'Easy' ? '🟢' : difficulty === 'Tough' ? '🔴' : difficulty === 'Moderate' ? '🟡' : '⚪',
      locationIcon: homeAway === 'Home' ? '🏠' : homeAway === 'Away' ? '✈️' : '🏟️',
      difficultyPercentile: difficultyContext,
      whyItMatters: difficulty === 'Easy' ? 'Favorable matchups significantly boost ceiling and floor - perfect spot to maximize this player' :
                    difficulty === 'Tough' ? 'Difficult matchups reduce upside potential - important to temper expectations and consider alternatives' :
                    'Neutral matchup means player talent drives results - rely on underlying skills and recent form',
      gameplanImpact: difficulty === 'Easy' ? 'Expect increased usage, positive game script, and multiple scoring opportunities' :
                      difficulty === 'Tough' ? 'May face reduced opportunities, challenging game script, or elite defensive schemes' :
                      'Standard expectations - player ability and role determine outcome more than matchup',
      weeklyDecision: difficulty === 'Easy' ? 'EXPLOIT THIS SPOT - Start with confidence and consider DFS tournament play' :
                      difficulty === 'Tough' ? 'PROCEED CAREFULLY - Bench if better options exist, avoid in tournaments' :
                      'TRUST THE TALENT - Player quality matters more than matchup in neutral spots'
    };
  };

  const interpretExperience = (yearsExp, draftYear) => {
    if (yearsExp === undefined && !draftYear) return null;
    
    const currentYear = 2025;
    const actualYears = yearsExp || (draftYear ? currentYear - draftYear : 0);
    
    let stage = '';
    let context = '';
    let outlook = '';
    let experienceContext = '';
    
    // Experience level percentile context
    const getExperienceContext = (years) => {
      if (years <= 2) return 'Bottom 20% experience level (Rookie class)';
      if (years <= 5) return 'Below average experience (Growth phase)';
      if (years <= 8) return 'Above average experience (Prime window)';
      if (years <= 12) return 'Top 25% experience (Veteran status)';
      return 'Top 5% experience (Elite tenure)';
    };
    
    experienceContext = getExperienceContext(actualYears);
    
    if (actualYears <= 2) {
      stage = 'Developing Talent';
      context = 'Early career growth phase';
      outlook = 'Learning and ascending';
    } else if (actualYears <= 5) {
      stage = 'Prime Development';
      context = 'Peak skill acquisition years';
      outlook = 'Breakout potential';
    } else if (actualYears <= 8) {
      stage = 'Veteran Presence';
      context = 'Peak performance window';
      outlook = 'Maximum value period';
    } else if (actualYears <= 12) {
      stage = 'Seasoned Professional';
      context = 'Experience-driven production';
      outlook = 'Sustained excellence';
    } else {
      stage = 'Elder Statesman';
      context = 'Late-career considerations';
      outlook = 'Decline monitoring needed';
    }
    
    return {
      years: actualYears,
      stage: `${stage} (${experienceContext})`,
      context,
      outlook,
      badge: actualYears <= 2 ? '🌱' : actualYears <= 5 ? '⚡' : actualYears <= 8 ? '🔥' : actualYears <= 12 ? '🎓' : '⏳',
      experiencePercentile: experienceContext,
      careerStage: actualYears <= 2 ? 'Rookie/Sophomore' : actualYears <= 5 ? 'Emerging' : actualYears <= 8 ? 'Established' : 'Veteran',
      whyItMatters: actualYears <= 2 ? 'Young players with limited experience often have untapped potential - perfect for growth and development' :
                    actualYears <= 5 ? 'Players in their development phase frequently take major steps forward - watch for breakout signs' :
                    actualYears <= 8 ? 'Established veterans combine experience with peak physical ability - reliable producers' :
                    actualYears <= 12 ? 'Seasoned professionals leverage experience to maintain production despite physical decline' :
                    'Long-tenured players rely heavily on experience and situation - monitor role security closely',
      developmentOutlook: actualYears <= 2 ? 'HIGH UPSIDE POTENTIAL - Major skill development and opportunity growth expected' :
                         actualYears <= 5 ? 'BREAKOUT WINDOW - Prime years for significant production increases' :
                         actualYears <= 8 ? 'PEAK PRODUCTION - Maximum combination of skill, experience, and opportunity' :
                         actualYears <= 12 ? 'STABLE PRODUCTION - Experience compensates for minor physical decline' :
                         'EXPERIENCE-DEPENDENT - Production heavily tied to role and situation',
      fantasyRelevance: actualYears <= 2 ? 'Dynasty gold mine, redraft sleeper potential with massive long-term value' :
                        actualYears <= 5 ? 'Prime breakout candidates - target aggressively before production spike' :
                        actualYears <= 8 ? 'Core roster building blocks - reliable production with continued upside' :
                        actualYears <= 12 ? 'Steady contributors - safe floor with veteran savvy and role security' :
                        'Situation-dependent assets - valuable when roles align, risky when change occurs'
    };
  };
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
          {/* Quick Scan Summary Section */}
          <div className={`${styles.card} ${styles.quickScanCard}`}>
            <h3>🔍 Quick Scan Summary</h3>
            <div className={styles.quickScanGrid}>
              
              {/* This Week's Decision */}
              {dossierResult.player_data.projected_points && (() => {
                const projectionInterpretation = interpretProjection(
                  dossierResult.player_data.projected_points,
                  dossierResult.player_data.position,
                  dossierResult.player_data.start_sit_grade
                );
                
                if (!projectionInterpretation) return null;
                
                return (
                  <div className={`${styles.quickScanItem} ${styles[`tier-${projectionInterpretation.tier || 'standard'}`]}`}>
                    <div className={styles.quickScanLabel}>This Week</div>
                    <div className={styles.quickScanValue}>
                      {projectionInterpretation.badge} {projectionInterpretation.tier === 'elite' ? 'MUST START' : 
                       projectionInterpretation.tier === 'excellent' ? 'STRONG START' :
                       projectionInterpretation.tier === 'solid' ? 'SAFE START' : 'CONSIDER'}
                    </div>
                    <div className={styles.quickScanContext}>{dossierResult.player_data.projected_points} pts projected</div>
                  </div>
                );
              })()}
              
              {/* Matchup Assessment */}
              {dossierResult.player_data.opponent && (() => {
                const matchupInterpretation = interpretMatchup(
                  dossierResult.player_data.opponent,
                  dossierResult.player_data.matchup_difficulty,
                  dossierResult.player_data.home_away
                );
                
                if (!matchupInterpretation) return null;
                
                return (
                  <div className={`${styles.quickScanItem} ${styles[`confidence-${matchupInterpretation.confidence || 'moderate'}`]}`}>
                    <div className={styles.quickScanLabel}>Matchup</div>
                    <div className={styles.quickScanValue}>
                      {matchupInterpretation.badge} {matchupInterpretation.assessment}
                    </div>
                    <div className={styles.quickScanContext}>vs {dossierResult.player_data.opponent}</div>
                  </div>
                );
              })()}
              
              {/* Value Assessment */}
              {dossierResult.player_data.value_1qb && (() => {
                const valueInterpretation = interpretValueScore(
                  dossierResult.player_data.value_1qb,
                  dossierResult.player_data.position
                );
                
                if (!valueInterpretation) return null;
                
                return (
                  <div className={`${styles.quickScanItem} ${styles[`tier-${valueInterpretation.tier}`]}`}>
                    <div className={styles.quickScanLabel}>Value</div>
                    <div className={styles.quickScanValue}>
                      {valueInterpretation.badge}
                    </div>
                    <div className={styles.quickScanContext}>{valueInterpretation.context}</div>
                  </div>
                );
              })()}
              
              {/* Ownership Opportunity */}
              {dossierResult.player_data.weekly_ownership !== undefined && (() => {
                const ownershipInterpretation = interpretOwnership(
                  dossierResult.player_data.weekly_ownership,
                  dossierResult.player_data.projected_points
                );
                
                if (!ownershipInterpretation) return null;
                
                return (
                  <div className={`${styles.quickScanItem} ${styles[ownershipInterpretation.tier]}`}>
                    <div className={styles.quickScanLabel}>Opportunity</div>
                    <div className={styles.quickScanValue}>
                      {ownershipInterpretation.badge} {ownershipInterpretation.competitiveEdge?.split(' - ')[0]}
                    </div>
                    <div className={styles.quickScanContext}>{dossierResult.player_data.weekly_ownership}% owned</div>
                  </div>
                );
              })()}
              
            </div>
          </div>

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
              
              {/* Enhanced data displays - Age and Career Stage */}
              {dossierResult.player_data.age && (() => {
                const ageInterpretation = interpretAgeTrajectory(
                  dossierResult.player_data.age,
                  dossierResult.player_data.age_category,
                  dossierResult.player_data.position
                );
                
                return (
                  <span className={styles.ageDisplay}>
                    <strong>Age:</strong> {ageInterpretation?.badge} {dossierResult.player_data.age} years old - {ageInterpretation?.trajectory}
                  </span>
                );
              })()}
              
              {(dossierResult.player_data.years_exp !== undefined || dossierResult.player_data.draft_year) && (() => {
                const experienceInterpretation = interpretExperience(
                  dossierResult.player_data.years_exp,
                  dossierResult.player_data.draft_year
                );
                
                return (
                  <span className={styles.experienceDisplay}>
                    <strong>Experience:</strong> {experienceInterpretation?.badge} {experienceInterpretation?.years} seasons - {experienceInterpretation?.stage}
                  </span>
                );
              })()}
              
              {/* Weekly projection with confidence */}
              {dossierResult.player_data.projected_points && (() => {
                const projectionInterpretation = interpretProjection(
                  dossierResult.player_data.projected_points,
                  dossierResult.player_data.position,
                  dossierResult.player_data.start_sit_grade
                );
                
                return (
                  <span className={styles.projectionDisplay}>
                    <strong>This Week:</strong> {projectionInterpretation?.badge} {dossierResult.player_data.projected_points} pts - {projectionInterpretation?.context}
                  </span>
                );
              })()}
              
              {dossierResult.player_data.start_sit_grade && (
                <span className={styles.gradeDisplay}>
                  <strong>Expert Confidence:</strong> Grade {dossierResult.player_data.start_sit_grade}
                  {dossierResult.player_data.grade_confidence_score && ` (${dossierResult.player_data.grade_confidence_score}% confidence)`}
                </span>
              )}
              
              {/* Current matchup information */}
              {dossierResult.player_data.opponent && (() => {
                const matchupInterpretation = interpretMatchup(
                  dossierResult.player_data.opponent,
                  dossierResult.player_data.matchup_difficulty,
                  dossierResult.player_data.home_away
                );
                
                return (
                  <span className={styles.matchupDisplay}>
                    <strong>Matchup:</strong> {matchupInterpretation?.badge} {matchupInterpretation?.locationIcon} vs {dossierResult.player_data.opponent} - {matchupInterpretation?.assessment}
                  </span>
                );
              })()}
              
              {/* Ownership percentage display */}
              {dossierResult.player_data.weekly_ownership !== undefined && (() => {
                const ownershipInterpretation = interpretOwnership(
                  dossierResult.player_data.weekly_ownership,
                  dossierResult.player_data.projected_points
                );
                
                return (
                  <span className={styles.ownershipDisplay}>
                    <strong>Ownership:</strong> {ownershipInterpretation?.badge} {dossierResult.player_data.weekly_ownership}% - {ownershipInterpretation?.context}
                  </span>
                );
              })()}
            </div>
          </div>

          {/* AI Analysis moved up: after Quick Scan + Player Overview */}
          <div className={`${styles.card} ${styles.aiAnalysisCard}`}>
            <h3>AI Analysis</h3>
            <div id="dossier-result" className={styles.resultBox} dangerouslySetInnerHTML={{ __html: converter.makeHtml(dossierResult.analysis) }}></div>
          </div>

          <div className={`${styles.card} ${styles.ecrDataCard} ${styles.priorityStandard}`}>
            <div className={styles.sectionPriorityIndicator}></div>
            <h3>Expert Consensus & Rankings</h3>
            <div className={styles.ecrGrid}>
              <div className={styles.ecrColumn}>
                <h4>Overall Expert Ranking</h4>
                <span>Expert Rank: {dossierResult.player_data.ecr_overall ? `${dossierResult.player_data.ecr_overall.toFixed(1)} (${getEstimatedDraftRound(dossierResult.player_data.ecr_overall)})` : 'N/A'}</span>
                <span title={`Expert Agreement Level: ${typeof dossierResult.player_data.sd_overall === 'number' ? dossierResult.player_data.sd_overall.toFixed(2) : 'N/A'}`}>
                  Expert Agreement: {getOverallSdLabel(dossierResult.player_data.sd_overall).icon} {getOverallSdLabel(dossierResult.player_data.sd_overall).label}
                </span>
                <span>Best: {dossierResult.player_data.best_overall || 'N/A'}</span>
                <span>Worst: {dossierResult.player_data.worst_overall || 'N/A'}</span>
                <span>Recent Momentum: {dossierResult.player_data.rank_delta_overall ? dossierResult.player_data.rank_delta_overall.toFixed(1) : 'N/A'}</span>
              </div>
              <div className={styles.ecrColumn}>
                <h4>Position Ranking</h4>
                <span>Position Rank: {dossierResult.player_data.ecr_positional ? dossierResult.player_data.ecr_positional.toFixed(1) : 'N/A'}</span>
                <span title={`Expert Agreement Level: ${typeof dossierResult.player_data.sd_positional === 'number' ? dossierResult.player_data.sd_positional.toFixed(2) : 'N/A'}`}>
                  Expert Agreement: {getPositionalSdLabel(dossierResult.player_data.sd_positional).icon} {getPositionalSdLabel(dossierResult.player_data.sd_positional).label}
                </span>
                <span>Best: {dossierResult.player_data.best_positional || 'N/A'}</span>
                <span>Worst: {dossierResult.player_data.worst_positional || 'N/A'}</span>
                <span>Recent Momentum: {dossierResult.player_data.rank_delta_positional ? dossierResult.player_data.rank_delta_positional.toFixed(1) : 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Weekly Outlook Section - PRIORITY FOCUS */}
          {(dossierResult.player_data.projected_points || dossierResult.player_data.start_sit_grade || dossierResult.player_data.opponent) && (
            <div className={`${styles.card} ${styles.weeklyOutlookCard} ${styles.priorityHigh}`}>
              <div className={styles.sectionPriorityIndicator}></div>
              <h3>📈 Weekly Outlook</h3>
              <div className={styles.weeklyGrid}>
                
                {/* Projected Points and Tier */}
                {dossierResult.player_data.projected_points && (() => {
                  const projectionInterpretation = interpretProjection(
                    dossierResult.player_data.projected_points, 
                    dossierResult.player_data.position,
                    dossierResult.player_data.start_sit_grade
                  );
                  
                  return (
                    <div className={styles.weeklySection}>
                      <h4>This Week's Outlook</h4>
                      <Tooltip content={
                        <div>
                          <h4>📊 Weekly Projection Analysis</h4>
                          <p><strong>Percentile Ranking:</strong> {projectionInterpretation?.percentileContext}</p>
                          <p><strong>Why This Matters:</strong> {projectionInterpretation?.whyItMatters}</p>
                          <div className={styles.tooltipSection}>
                            <strong>Methodology:</strong>
                            <ul>
                              <li>Combines expert projections with historical performance</li>
                              <li>Factors in matchup difficulty and game script</li>
                              <li>Adjusted for position-specific scoring patterns</li>
                            </ul>
                          </div>
                        </div>
                      } detailed>
                        <span className={`${styles.chip} ${styles.projectionBadge} ${styles[projectionInterpretation?.tier || 'standard']}`}>
                          {projectionInterpretation?.badge} {projectionInterpretation?.context}
                        </span>
                      </Tooltip>
                      <span className={styles.projectionDetails}>
                        {dossierResult.player_data.projected_points} points - {projectionInterpretation?.confidence}
                      </span>
                      {dossierResult.player_data.start_sit_grade && (
                        <span className={styles.gradeConfidence}>
                          Grade {dossierResult.player_data.start_sit_grade}
                          {dossierResult.player_data.grade_confidence_score && 
                            ` (${dossierResult.player_data.grade_confidence_score}% confidence)`
                          }
                        </span>
                      )}
                      
                      {/* Actionable Start/Sit Recommendation */}
                      {projectionInterpretation?.startSitGuidance && (
                        <div className={`${styles.actionableRecommendation} ${styles[`tier-${projectionInterpretation?.tier}`]}`}>
                          <strong>💡 This Week's Decision:</strong> {projectionInterpretation?.startSitGuidance}
                        </div>
                      )}
                      
                      {/* Weekly Strategy Guidance */}
                      {projectionInterpretation?.weeklyStrategy && (
                        <div className={styles.strategyGuidance}>
                          <strong>🎯 Strategy:</strong> {projectionInterpretation?.weeklyStrategy}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Matchup Analysis */}
                {dossierResult.player_data.opponent && (() => {
                  const matchupInterpretation = interpretMatchup(
                    dossierResult.player_data.opponent,
                    dossierResult.player_data.matchup_difficulty,
                    dossierResult.player_data.home_away
                  );
                  
                  return (
                    <div className={styles.weeklySection}>
                      <h4>This Week's Matchup</h4>
                      <Tooltip content={
                        <div>
                          <h4>⚔️ Matchup Analysis</h4>
                          <p><strong>Difficulty Level:</strong> {matchupInterpretation?.difficultyPercentile}</p>
                          <p><strong>Why This Matters:</strong> {matchupInterpretation?.whyItMatters}</p>
                          <div className={styles.tooltipSection}>
                            <strong>Analysis Factors:</strong>
                            <ul>
                              <li>Opponent defensive rankings vs position</li>
                              <li>Historical matchup performance</li>
                              <li>Home/away field considerations</li>
                              <li>Weather and game script projections</li>
                            </ul>
                          </div>
                        </div>
                      } detailed>
                        <span className={`${styles.chip} ${styles.matchupBadge} ${styles[matchupInterpretation?.confidence || 'moderate']}`}>
                          {matchupInterpretation?.badge} {matchupInterpretation?.assessment}
                        </span>
                      </Tooltip>
                      <span className={styles.matchupDetails}>
                        {matchupInterpretation?.locationIcon} vs {dossierResult.player_data.opponent} ({matchupInterpretation?.locationContext})
                      </span>
                      <span className={`${styles.matchupRecommendation} ${styles[`confidence-${matchupInterpretation?.confidence}`]}`}>
                        💡 {matchupInterpretation?.recommendation} - {matchupInterpretation?.context}
                      </span>
                      
                      {/* Weekly Decision Guidance */}
                      {matchupInterpretation?.weeklyDecision && (
                        <div className={`${styles.actionableRecommendation} ${styles[`confidence-${matchupInterpretation?.confidence}`]}`}>
                          <strong>⚡ Weekly Decision:</strong> {matchupInterpretation?.weeklyDecision}
                        </div>
                      )}
                      
                      {/* Game Plan Impact */}
                      {matchupInterpretation?.gameplanImpact && (
                        <div className={styles.gameplanImpact}>
                          <strong>📋 Game Plan Impact:</strong> {matchupInterpretation?.gameplanImpact}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Schedule Preview */}
                {dossierResult.player_data.schedule_outlook && (
                  <div className={styles.weeklySection}>
                    <h4>Schedule Preview</h4>
                    <span className={styles.scheduleOutlook}>
                      {dossierResult.player_data.schedule_outlook}
                    </span>
                  </div>
                )}

              </div>
            </div>
          )}

          {/* Market Analysis Section */}
          {(dossierResult.player_data.weekly_ownership || dossierResult.player_data.value_1qb || dossierResult.player_data.value_opportunity_score) && (
            <div className={`${styles.card} ${styles.marketAnalysisCard} ${styles.priorityMedium}`}>
              <div className={styles.sectionPriorityIndicator}></div>
              <h3>💰 Fantasy Value Analysis</h3>
              <div className={styles.marketGrid}>
                
                {/* Ownership vs Projection */}
                {dossierResult.player_data.weekly_ownership !== undefined && dossierResult.player_data.projected_points && (() => {
                  const ownershipInterpretation = interpretOwnership(
                    dossierResult.player_data.weekly_ownership,
                    dossierResult.player_data.projected_points
                  );
                  
                  return (
                    <div className={styles.marketSection}>
                      <h4>Roster Popularity</h4>
                      <Tooltip content={
                        <div>
                          <h4>👥 Roster Popularity Analysis</h4>
                          <p><strong>Ownership Level:</strong> {ownershipInterpretation?.percentileContext}</p>
                          <p><strong>Competitive Edge:</strong> {ownershipInterpretation?.competitiveEdge}</p>
                          <p><strong>Why This Matters:</strong> {ownershipInterpretation?.whyItMatters}</p>
                          <div className={styles.tooltipSection}>
                            <strong>Strategic Implications:</strong>
                            <ul>
                              <li>Lower ownership = bigger advantage if player performs</li>
                              <li>Higher ownership = less differentiation opportunity</li>
                              <li>Availability assessment for waiver pickups</li>
                              <li>Tournament leverage considerations</li>
                            </ul>
                          </div>
                        </div>
                      } detailed>
                        <span className={`${styles.chip} ${styles.ownershipBadge} ${styles[ownershipInterpretation?.tier]}`}>
                          {ownershipInterpretation?.badge} {ownershipInterpretation?.context}
                        </span>
                      </Tooltip>
                      <span className={styles.ownershipDetails}>
                        {dossierResult.player_data.weekly_ownership}% owned - {ownershipInterpretation?.opportunity}
                      </span>
                      <span className={styles.projectionContext}>
                        {dossierResult.player_data.projected_points} point projection
                      </span>
                      
                      {/* Competitive Edge Analysis */}
                      {ownershipInterpretation?.competitiveEdge && (
                        <div className={`${styles.competitiveEdge} ${styles[ownershipInterpretation?.tier]}`}>
                          <strong>🏆 Competitive Edge:</strong> {ownershipInterpretation?.competitiveEdge}
                        </div>
                      )}
                      
                      {/* Fantasy Impact */}
                      {ownershipInterpretation?.fantasyImpact && (
                        <div className={styles.fantasyImpact}>
                          <strong>🎯 Fantasy Impact:</strong> {ownershipInterpretation?.fantasyImpact}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Market Value (supports 1QB or 2QB fallback) */}
                {(dossierResult.player_data.value_1qb || dossierResult.player_data.value_2qb) && (() => {
                  const pos = dossierResult.player_data.position;
                  const valueScore = (typeof dossierResult.player_data.value_1qb === 'number' ? dossierResult.player_data.value_1qb : null)
                    ?? (typeof dossierResult.player_data.value_2qb === 'number' ? dossierResult.player_data.value_2qb : null);
                  const valueInterpretation = valueScore != null ? interpretValueScore(valueScore, pos) : null;
                  const formatLabel = (dossierResult.player_data.value_1qb != null) ? '1QB format' : '2QB/Superflex format';
                  if (!valueInterpretation) return null;
                  
                  return (
                    <div className={styles.marketSection}>
                      <h4>Draft & Trade Value</h4>
                      <Tooltip content={
                        <div>
                          <h4>💰 Draft & Trade Value Analysis</h4>
                          <p><strong>Value Tier:</strong> {valueInterpretation?.context}</p>
                          <p><strong>Score Context:</strong> {valueInterpretation?.scoreContext}</p>
                          <p><strong>Why This Matters:</strong> {valueInterpretation?.whyItMatters}</p>
                          <p><em>Format:</em> {formatLabel}</p>
                          <div className={styles.tooltipSection}>
                            <strong>Calculation Method:</strong>
                            <ul>
                              <li>ADP vs projected season points</li>
                              <li>Position scarcity adjustments</li>
                              <li>League format considerations</li>
                              <li>Historical value trend analysis</li>
                            </ul>
                          </div>
                        </div>
                      } detailed>
                        <span className={`${styles.chip} ${styles.valueBadge} ${styles[valueInterpretation?.tier]}`}>
                          {valueInterpretation?.badge}
                        </span>
                      </Tooltip>
                      <span className={styles.valueDescription}>
                        {valueInterpretation?.description} - {valueInterpretation?.context}
                      </span>
                      {valueScore != null && (
                        <span className={styles.valueScore}>
                          Draft Rating: {valueScore} pts{dossierResult.player_data.value_2qb && dossierResult.player_data.value_1qb != null && ` (Superflex: ${dossierResult.player_data.value_2qb} pts)`}
                        </span>
                      )}
                    </div>
                  );
                })()}

                {/* Value Opportunity */}
                {dossierResult.player_data.value_opportunity_score && (() => {
                  const opportunityInterpretation = interpretOpportunityScore(
                    dossierResult.player_data.value_opportunity_score,
                    dossierResult.player_data.weekly_ownership
                  );
                  
                  return (
                    <div className={styles.marketSection}>
                      <h4>Waiver Wire Priority</h4>
                      <span className={`${styles.chip} ${styles.opportunityBadge} ${styles[opportunityInterpretation?.tier]}`}>
                        {opportunityInterpretation?.badge}
                      </span>
                      <span className={styles.opportunityDescription}>
                        {opportunityInterpretation?.description} - {opportunityInterpretation?.context}
                      </span>
                      <span className={styles.opportunityAction}>
                        💡 {opportunityInterpretation?.action}
                      </span>
                      
                      {/* Urgency Indicator */}
                      {opportunityInterpretation?.urgency && (
                        <div className={`${styles.urgencyIndicator} ${styles[opportunityInterpretation?.tier]}`}>
                          <strong>⏰ Urgency:</strong> {opportunityInterpretation?.urgency}
                        </div>
                      )}
                      
                      {/* Fantasy Impact */}
                      {opportunityInterpretation?.fantasyImpact && (
                        <div className={styles.waiverFantasyImpact}>
                          <strong>🚀 Impact:</strong> {opportunityInterpretation?.fantasyImpact}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Acquisition Priority */}
                {(dossierResult.player_data.weekly_ownership !== undefined && dossierResult.player_data.projected_points) && (
                  <div className={styles.marketSection}>
                    <h4>Acquisition Priority</h4>
                    {(() => {
                      const ownership = dossierResult.player_data.weekly_ownership;
                      const projection = dossierResult.player_data.projected_points;
                      let priority = '';
                      let priorityClass = '';
                      
                      if (ownership < 10 && projection >= 17) {
                        priority = '🔥 Immediate Target';
                        priorityClass = 'priorityImmediate';
                      } else if (ownership < 25 && projection >= 15) {
                        priority = '🎯 High Priority';
                        priorityClass = 'priorityHigh';
                      } else if (ownership < 50 && projection >= 12) {
                        priority = '📈 Monitor Closely';
                        priorityClass = 'priorityMedium';
                      } else if (ownership > 90) {
                        priority = '❌ Likely Unavailable';
                        priorityClass = 'priorityUnavailable';
                      } else {
                        priority = '📊 Standard Interest';
                        priorityClass = 'priorityStandard';
                      }
                      
                      return (
                        <span className={`${styles.acquisitionPriority} ${styles[priorityClass]}`}>
                          {priority}
                        </span>
                      );
                    })()}
                  </div>
                )}

              </div>
            </div>
          )}

          {/* Age Trajectory Section */}
          {(dossierResult.player_data.age || dossierResult.player_data.age_category || dossierResult.player_data.draft_year) && (
            <div className={`${styles.card} ${styles.ageTrajectoryCard} ${styles.priorityStandard}`}>
              <div className={styles.sectionPriorityIndicator}></div>
              <h3>📅 Age & Development Trajectory</h3>
              <div className={styles.ageGrid}>
                
                {/* Age Analysis */}
                {dossierResult.player_data.age && (() => {
                  const ageInterpretation = interpretAgeTrajectory(
                    dossierResult.player_data.age,
                    dossierResult.player_data.age_category,
                    dossierResult.player_data.position
                  );
                  
                  return (
                    <div className={styles.ageSection}>
                      <h4>Age Analysis</h4>
                      <span className={`${styles.ageBadge} ${styles[ageInterpretation?.urgency]}`}>
                        {ageInterpretation?.badge} {ageInterpretation?.trajectory}
                      </span>
                      <span className={styles.ageOutlook}>
                        {dossierResult.player_data.age} years old - {ageInterpretation?.outlook}
                      </span>
                      <span className={styles.ageStrategy}>
                        💡 {ageInterpretation?.strategy}
                      </span>
                      
                      {/* Roster Strategy Guidance */}
                      {ageInterpretation?.rosterStrategy && (
                        <div className={`${styles.rosterStrategy} ${styles[ageInterpretation?.urgency]}`}>
                          <strong>📈 Roster Strategy:</strong> {ageInterpretation?.rosterStrategy}
                        </div>
                      )}
                      
                      {/* Timeline Guidance */}
                      {ageInterpretation?.timelineGuidance && (
                        <div className={styles.timelineGuidance}>
                          <strong>⏳ Timeline:</strong> {ageInterpretation?.timelineGuidance}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Career Stage */}
                {dossierResult.player_data.draft_year && (
                  <div className={styles.ageSection}>
                    <h4>Career Stage</h4>
                    <span className={styles.draftInfo}>
                      Drafted: {dossierResult.player_data.draft_year}
                    </span>
                    {dossierResult.player_data.years_exp !== undefined && (
                      <span className={styles.experience}>
                        {dossierResult.player_data.years_exp} seasons experience
                      </span>
                    )}
                    {(() => {
                      const currentYear = 2025;
                      const yearsExp = currentYear - dossierResult.player_data.draft_year;
                      let careerStage = '';
                      let stageClass = '';
                      
                      if (yearsExp <= 2) {
                        careerStage = '🌱 Early Career - Development Phase';
                        stageClass = 'stageEarly';
                      } else if (yearsExp <= 5) {
                        careerStage = '⚡ Prime Development - Peak Growth';
                        stageClass = 'stageDevelopment';
                      } else if (yearsExp <= 8) {
                        careerStage = '🔥 Peak Performance - Maximum Value';
                        stageClass = 'stagePeak';
                      } else if (yearsExp <= 12) {
                        careerStage = '🎓 Veteran Stage - Experience Balance';
                        stageClass = 'stageVeteran';
                      } else {
                        careerStage = '⏳ Late Career - Decline Considerations';
                        stageClass = 'stageLate';
                      }
                      
                      return (
                        <span className={`${styles.careerStage} ${styles[stageClass]}`}>
                          {careerStage}
                        </span>
                      );
                    })()}
                  </div>
                )}

                {/* Performance Trajectory */}
                {(dossierResult.player_data.age && dossierResult.player_data.position) && (
                  <div className={styles.ageSection}>
                    <h4>Performance Outlook</h4>
                    {(() => {
                      const age = dossierResult.player_data.age;
                      const position = dossierResult.player_data.position;
                      let trajectory = '';
                      let trajectoryClass = '';
                      
                      if (position === 'RB') {
                        if (age <= 25) {
                          trajectory = '🚀 Prime RB Years - Peak Performance Expected';
                          trajectoryClass = 'trajectoryPeak';
                        } else if (age <= 28) {
                          trajectory = '⏰ Good Production Window Remaining';
                          trajectoryClass = 'trajectoryGood';
                        } else {
                          trajectory = '⚠️ Age-Related Decline Risk Increasing';
                          trajectoryClass = 'trajectoryRisk';
                        }
                      } else if (position === 'QB') {
                        if (age <= 30) {
                          trajectory = '📈 Ascending or Peak QB Performance';
                          trajectoryClass = 'trajectoryAscending';
                        } else if (age <= 35) {
                          trajectory = '🎯 Prime QB Performance Years';
                          trajectoryClass = 'trajectoryPrime';
                        } else {
                          trajectory = '⚖️ Experience vs Physical Decline';
                          trajectoryClass = 'trajectoryBalance';
                        }
                      } else {
                        if (age <= 27) {
                          trajectory = '🌟 Prime Years Ahead or Current';
                          trajectoryClass = 'trajectoryPrime';
                        } else if (age <= 32) {
                          trajectory = '🔥 Peak Performance Window';
                          trajectoryClass = 'trajectoryPeak';
                        } else {
                          trajectory = '📊 Age-Related Decline Considerations';
                          trajectoryClass = 'trajectoryConsider';
                        }
                      }
                      
                      return (
                        <span className={`${styles.trajectory} ${styles[trajectoryClass]}`}>
                          {trajectory}
                        </span>
                      );
                    })()}
                  </div>
                )}

                {/* Dynasty vs Redraft Implications */}
                {(dossierResult.player_data.age && dossierResult.player_data.age_category) && (
                  <div className={styles.ageSection}>
                    <h4>Roster Strategy</h4>
                    {(() => {
                      const ageCategory = dossierResult.player_data.age_category;
                      let strategy = '';
                      let strategyClass = '';
                      
                      if (ageCategory.includes('Ascending') || ageCategory.includes('Development')) {
                        strategy = '💎 Dynasty: Buy | Redraft: Growth potential';
                        strategyClass = 'strategyBuy';
                      } else if (ageCategory.includes('Prime') || ageCategory.includes('Peak')) {
                        strategy = '🎯 Dynasty: Hold | Redraft: Core asset';
                        strategyClass = 'strategyHold';
                      } else if (ageCategory.includes('Decline') || ageCategory.includes('Risk')) {
                        strategy = '⏰ Dynasty: Consider selling | Redraft: Monitor';
                        strategyClass = 'strategySell';
                      } else {
                        strategy = '📊 Dynasty: Evaluate | Redraft: Standard';
                        strategyClass = 'strategyStandard';
                      }
                      
                      return (
                        <span className={`${styles.strategy} ${styles[strategyClass]}`}>
                          {strategy}
                        </span>
                      );
                    })()}
                  </div>
                )}

              </div>
            </div>
          )}

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
