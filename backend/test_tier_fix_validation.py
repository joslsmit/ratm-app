#!/usr/bin/env python3
"""
Test script to validate the tier-based waiver analysis fixes
Tests the specific C.J. Stroud (QB2) vs Lamar Jackson (QB1) scenario that was problematic
"""

import requests
import json
import time

def test_tier_based_fixes():
    """Test the enhanced waiver_swap_analysis with tier-based decision framework."""
    
    print("🧪 Testing Tier-Based Waiver Analysis Fixes")
    print("=" * 60)
    print("Scenario: Should we add Lamar Jackson (QB1) and drop C.J. Stroud (QB2)?")
    print("Expected: Clear ADD recommendation with tier upgrade reasoning")
    print()
    
    # Test data mimicking the user's problematic scenario
    test_data = {
        "roster": {
            "qb": "C.J. Stroud",  # QB2 (user's current QB)
            "rb1": "Christian McCaffrey", 
            "rb2": "Saquon Barkley",
            "wr1": "Tyreek Hill",
            "wr2": "Stefon Diggs",
            "te": "Travis Kelce",
            "flex": "Mike Evans",
            "k": "Justin Tucker",
            "def": "San Francisco"
        },
        "player_to_add": "Lamar Jackson",  # QB1 (elite upgrade target)
        "ecr_type_preference": "overall"
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("📡 Making request to waiver_swap_analysis endpoint...")
        start_time = time.time()
        
        response = requests.post(
            'http://localhost:5000/api/waiver_swap_analysis',
            json=test_data,
            headers=headers,
            timeout=60
        )
        
        elapsed_time = time.time() - start_time
        print(f"⏱️  Response time: {elapsed_time:.1f} seconds")
        print()
        
        if response.status_code == 200:
            result = response.json()
            analysis_result = result.get('result', '')
            
            print("✅ REQUEST SUCCESSFUL")
            print("=" * 40)
            print("AI ANALYSIS RESULT:")
            print("-" * 40)
            print(analysis_result)
            print()
            
            # Validate tier-based decision making
            print("🔍 VALIDATION CHECKS:")
            print("-" * 25)
            
            # Check for tier recognition
            has_tier_recognition = any(tier in analysis_result.upper() for tier in ['QB1', 'QB2', 'TIER'])
            print(f"✓ Tier Recognition: {'PASS' if has_tier_recognition else 'FAIL'}")
            
            # Check for upgrade logic
            has_upgrade_logic = any(phrase in analysis_result.upper() for phrase in ['UPGRADE', 'TIER UPGRADE', 'QB1', 'ELITE'])
            print(f"✓ Upgrade Logic: {'PASS' if has_upgrade_logic else 'FAIL'}")
            
            # Check for clear recommendation
            has_clear_add = 'ADD' in analysis_result.upper() and 'DO NOT ADD' not in analysis_result.upper()
            print(f"✓ Clear ADD Recommendation: {'PASS' if has_clear_add else 'FAIL'}")
            
            # Check for Jackson vs Stroud comparison
            mentions_both_players = 'LAMAR' in analysis_result.upper() and 'STROUD' in analysis_result.upper()
            print(f"✓ Player Comparison: {'PASS' if mentions_both_players else 'FAIL'}")
            
            # Check for tier-based reasoning
            has_tier_reasoning = any(phrase in analysis_result.upper() for phrase in ['QB2', 'QB1', 'TIER', 'TOP 12'])
            print(f"✓ Tier-Based Reasoning: {'PASS' if has_tier_reasoning else 'FAIL'}")
            
            print()
            
            # Overall assessment
            all_checks_pass = all([
                has_tier_recognition,
                has_upgrade_logic, 
                has_clear_add,
                mentions_both_players,
                has_tier_reasoning
            ])
            
            if all_checks_pass:
                print("🎉 ALL VALIDATION CHECKS PASSED!")
                print("✅ Tier-based fixes are working correctly")
                print("✅ AI now properly recognizes QB1 > QB2 upgrades")
            else:
                print("⚠️  Some validation checks failed")
                print("❌ Further enhancement may be needed")
            
            return all_checks_pass
            
        else:
            print(f"❌ REQUEST FAILED")
            print(f"Status Code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Tier-Based Fix Validation Test")
    print()
    success = test_tier_based_fixes()
    print()
    if success:
        print("🎯 CONCLUSION: Tier-based waiver analysis fixes are working correctly!")
    else:
        print("🔧 CONCLUSION: Additional fixes may be needed")