#!/usr/bin/env python3
"""
Test script for enhanced waiver_swap_analysis endpoint (Phase 0B)
Tests the waiver wire add/drop analysis with enhanced prompting system.
"""

import requests
import json
import os

def test_waiver_swap_analysis():
    """Test the enhanced waiver_swap_analysis endpoint."""
    
    # Test data: realistic fantasy roster with waiver pickup scenario
    test_data = {
        "roster": {
            "QB1": "Josh Allen",
            "RB1": "Christian McCaffrey", 
            "RB2": "Saquon Barkley",
            "WR1": "Cooper Kupp",
            "WR2": "Stefon Diggs",
            "TE1": "Travis Kelce",
            "FLEX": "Chris Olave",
            "DEF": "49ers D/ST",
            "K": "Justin Tucker",
            "BENCH1": "Gus Edwards",
            "BENCH2": "Jaylen Waddle", 
            "BENCH3": "Romeo Doubs",
            "BENCH4": "Trey McBride",
            "BENCH5": "Kyler Murray",
            "BENCH6": "Rhamondre Stevenson"
        },
        "player_to_add": "Tank Bigsby",  # Rising RB with opportunity
        "ecr_type_preference": "overall"
    }
    
    print("🔍 Testing Enhanced Waiver Swap Analysis Endpoint")
    print("=" * 60)
    print(f"Waiver candidate: {test_data['player_to_add']}")
    print(f"Roster size: {len([p for p in test_data['roster'].values() if p])}")
    print()
    
    # Test with mock API key
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': 'test_api_key_mock_for_development'
    }
    
    try:
        print("📡 Making request to waiver_swap_analysis endpoint...")
        response = requests.post(
            'http://localhost:5000/api/waiver_swap_analysis',
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            analysis_result = result.get('result', '')
            
            print("\n✅ ENHANCED WAIVER SWAP ANALYSIS RESULT:")
            print("=" * 60)
            print(analysis_result)
            print("=" * 60)
            
            # Validate enhanced analysis characteristics
            analysis_checks = {
                "has_confidence_badge": any(emoji in analysis_result for emoji in ['✅', '🤔', '⚠️']),
                "has_methodology": "WAIVER CANDIDATE VALUE ASSESSMENT" in analysis_result or "VALUE ASSESSMENT" in analysis_result,
                "has_add_drop_decision": any(decision in analysis_result.upper() for decision in ['ADD', 'DROP', 'DO NOT ADD']),
                "analysis_length": len(analysis_result),
                "has_player_context": "ECR" in analysis_result,
                "has_roster_analysis": "ROSTER" in analysis_result.upper() or "BENCH" in analysis_result.upper(),
                "structured_analysis": analysis_result.count('**') >= 4  # Multiple structured sections
            }
            
            print("\n📊 ENHANCED ANALYSIS VALIDATION:")
            print("-" * 40)
            for check, result in analysis_checks.items():
                status = "✅" if result else "❌"
                print(f"{status} {check}: {result}")
            
            # Quality assessment
            is_enhanced = (
                analysis_checks["has_confidence_badge"] and
                analysis_checks["has_add_drop_decision"] and
                analysis_checks["analysis_length"] > 1000 and
                analysis_checks["structured_analysis"]
            )
            
            if is_enhanced:
                print("\n🎉 PHASE 0B ENHANCEMENT CONFIRMED!")
                print("   Analysis shows sophisticated waiver wire decision-making")
                print("   with enhanced context and structured methodology.")
            else:
                print("\n⚠️  Enhancement validation needs attention")
                print("   Some Phase 0B characteristics may be missing")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        print("\n💡 Make sure the backend server is running on http://localhost:5000")

if __name__ == "__main__":
    test_waiver_swap_analysis()