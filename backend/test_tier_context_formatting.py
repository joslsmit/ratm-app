#!/usr/bin/env python3
"""
Test script to validate tier-based context formatting improvements
Tests the enhanced context formatting for C.J. Stroud vs Lamar Jackson scenario
"""

import sys
import os

# Add the current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from context_formatters import ContextFormatter, AnalysisType

def test_tier_context_formatting():
    """Test the enhanced context formatting with tier classifications."""
    
    print("🧪 Testing Enhanced Context Formatting with Tier Classifications")
    print("=" * 70)
    print()
    
    # Mock player data for C.J. Stroud (QB2)
    cj_stroud_data = {
        'name': 'C.J. Stroud',
        'position': 'QB',
        'team': 'HOU',
        'years_exp': 1,
        'is_rookie': False,
        'bye_week': 14,
        'ecr_overall': 85.2,
        'ecr_positional': 18.3,  # QB #18 (QB2 territory)
        'sd_overall': 4.2,
        'best_overall': 78,
        'worst_overall': 95,
        'rank_delta_overall': 2.1
    }
    
    # Mock player data for Lamar Jackson (QB1)
    lamar_jackson_data = {
        'name': 'Lamar Jackson',
        'position': 'QB',
        'team': 'BAL',
        'years_exp': 7,
        'is_rookie': False,
        'bye_week': 14,
        'ecr_overall': 8.7,
        'ecr_positional': 1.67,  # QB #1.67 (Elite QB1)
        'sd_overall': 0.8,
        'best_overall': 1,
        'worst_overall': 3,
        'rank_delta_overall': -0.5
    }
    
    print("🔍 TESTING C.J. STROUD (Expected: QB2 Classification)")
    print("-" * 50)
    stroud_context = ContextFormatter.format_enhanced_player_context(
        cj_stroud_data, AnalysisType.WAIVER_ANALYSIS
    )
    print(stroud_context)
    print()
    
    print("🔍 TESTING LAMAR JACKSON (Expected: QB1 Classification)")
    print("-" * 50)
    jackson_context = ContextFormatter.format_enhanced_player_context(
        lamar_jackson_data, AnalysisType.WAIVER_ANALYSIS
    )
    print(jackson_context)
    print()
    
    # Validation checks
    print("🔍 VALIDATION CHECKS:")
    print("-" * 25)
    
    # Check C.J. Stroud tier classification
    stroud_has_qb2 = 'QB2' in stroud_context and 'Backup/Streaming' in stroud_context
    print(f"✓ C.J. Stroud QB2 Classification: {'PASS' if stroud_has_qb2 else 'FAIL'}")
    
    # Check Lamar Jackson tier classification  
    jackson_has_qb1 = 'QB1' in jackson_context and 'Elite/Starter' in jackson_context
    print(f"✓ Lamar Jackson QB1 Classification: {'PASS' if jackson_has_qb1 else 'FAIL'}")
    
    # Check positional rank display
    stroud_has_rank = 'QB#18' in stroud_context or 'QB #18' in stroud_context
    jackson_has_rank = 'QB#1' in jackson_context or 'QB #1' in jackson_context
    print(f"✓ Positional Rank Display: {'PASS' if stroud_has_rank and jackson_has_rank else 'FAIL'}")
    
    # Check waiver value assessment
    stroud_has_value = any(phrase in stroud_context for phrase in ['Solid Addition', 'Depth/Streaming'])
    jackson_has_value = 'High-Value Pickup' in jackson_context
    print(f"✓ Value Assessment Logic: {'PASS' if stroud_has_value and jackson_has_value else 'FAIL'}")
    
    # Check trend indicators
    has_trend_indicators = '📈' in stroud_context or '🔥' in jackson_context or 'Trending' in stroud_context or 'Rising' in jackson_context
    print(f"✓ Trend Indicators: {'PASS' if has_trend_indicators else 'FAIL'}")
    
    print()
    
    # Overall assessment
    all_checks_pass = all([
        stroud_has_qb2,
        jackson_has_qb1,
        stroud_has_rank,
        jackson_has_rank,
        stroud_has_value,
        jackson_has_value
    ])
    
    if all_checks_pass:
        print("🎉 ALL VALIDATION CHECKS PASSED!")
        print("✅ Enhanced context formatting is working correctly")
        print("✅ Tier classifications (QB1 vs QB2) are properly displayed")
        print("✅ AI will now receive clear tier context for better decisions")
    else:
        print("⚠️  Some validation checks failed")
        print("❌ Context formatting may need additional enhancement")
    
    return all_checks_pass

if __name__ == "__main__":
    print("🚀 Starting Enhanced Context Formatting Test")
    print()
    success = test_tier_context_formatting()
    print()
    if success:
        print("🎯 CONCLUSION: Enhanced context formatting with tier classifications is working!")
        print("📊 The AI will now receive clear QB1 vs QB2 tier information for better analysis")
    else:
        print("🔧 CONCLUSION: Context formatting enhancements need review")