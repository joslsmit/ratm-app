#!/usr/bin/env python3
"""
Test script for enhanced waiver_wire_analysis endpoint using curl
"""

import subprocess
import json
import sys

def test_waiver_wire_analysis():
    """Test the enhanced waiver_wire_analysis endpoint using curl."""
    
    # Test data: realistic fantasy roster for waiver analysis
    test_data = {
        "team_roster": [
            "Josh Allen",
            "Christian McCaffrey", 
            "Saquon Barkley",
            "Cooper Kupp",
            "Stefon Diggs",
            "Travis Kelce",
            "Chris Olave",
            "Gus Edwards",
            "Jaylen Waddle", 
            "Romeo Doubs",
            "Trey McBride",
            "Kyler Murray",
            "Rhamondre Stevenson",
            "49ers D/ST",
            "Justin Tucker"
        ],
        "ecr_type_preference": "overall"
    }
    
    print("🔍 Testing Enhanced Waiver Wire Analysis Endpoint")
    print("=" * 60)
    print(f"Team roster size: {len(test_data['team_roster'])}")
    print("Testing waiver wire recommendations and drop candidates...")
    print()
    
    # Prepare curl command
    curl_cmd = [
        "curl",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", "X-API-Key: test_api_key_mock_for_development",
        "-d", json.dumps(test_data),
        "--max-time", "45",
        "--silent",
        "--show-error",
        "http://localhost:5000/api/waiver_wire_analysis"
    ]
    
    try:
        print("📡 Making curl request to waiver_wire_analysis endpoint...")
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=50)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                analysis_result = response_data.get('result', '')
                
                print("\n✅ ENHANCED WAIVER WIRE ANALYSIS RESULT:")
                print("=" * 60)
                print(analysis_result)
                print("=" * 60)
                
                # Validate enhanced analysis characteristics
                analysis_checks = {
                    "has_confidence_badge": any(emoji in analysis_result for emoji in ['✅', '🤔', '⚠️']),
                    "has_methodology": "ROSTER NEEDS ASSESSMENT" in analysis_result or "AVAILABLE PLAYER" in analysis_result,
                    "has_recommendations": any(keyword in analysis_result.upper() for keyword in ['RECOMMEND', 'ADD', 'DROP']),
                    "analysis_length": len(analysis_result),
                    "has_player_context": "ECR" in analysis_result,
                    "has_waiver_strategy": "WAIVER" in analysis_result.upper() or "PRIORITY" in analysis_result.upper(),
                    "structured_analysis": analysis_result.count('**') >= 6,  # Multiple structured sections
                    "has_rationale": any(word in analysis_result.lower() for word in ['because', 'due to', 'reasoning', 'rationale'])
                }
                
                print("\n📊 ENHANCED ANALYSIS VALIDATION:")
                print("-" * 40)
                for check, result_val in analysis_checks.items():
                    status = "✅" if result_val else "❌"
                    print(f"{status} {check}: {result_val}")
                
                # Waiver-specific checks
                waiver_specific_checks = {
                    "mentions_multiple_players": analysis_result.count('ECR') >= 3,
                    "has_add_recommendations": any(word in analysis_result.upper() for word in ['ADD', 'CLAIM', 'PICK UP']),
                    "has_drop_suggestions": "DROP" in analysis_result.upper(),
                    "considers_roster_needs": any(word in analysis_result.lower() for word in ['depth', 'weakness', 'need', 'position']),
                    "has_priority_order": any(word in analysis_result.lower() for word in ['priority', 'order', 'first', 'second', 'third'])
                }
                
                print("\n🎯 WAIVER-SPECIFIC VALIDATION:")
                print("-" * 40) 
                for check, result_val in waiver_specific_checks.items():
                    status = "✅" if result_val else "❌"
                    print(f"{status} {check}: {result_val}")
                
                # Overall assessment
                is_enhanced = (
                    analysis_checks["has_confidence_badge"] and
                    analysis_checks["has_methodology"] and
                    analysis_checks["analysis_length"] > 1500 and
                    analysis_checks["structured_analysis"] and
                    waiver_specific_checks["has_add_recommendations"]
                )
                
                if is_enhanced:
                    print("\n🎉 PHASE 0B ENHANCEMENT CONFIRMED!")
                    print("   Analysis shows sophisticated waiver wire strategy")
                    print("   with enhanced context and structured methodology.")
                    print(f"   Response length: {analysis_checks['analysis_length']} characters")
                else:
                    print("\n⚠️  Enhancement validation needs attention")
                    print("   Some Phase 0B characteristics may be missing")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print("Raw response:", result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
                
        else:
            print(f"❌ Curl request failed with return code {result.returncode}")
            if result.stderr:
                print("Error:", result.stderr)
            if result.stdout:
                print("Output:", result.stdout[:200])
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out after 50 seconds")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        
    print("\n💡 Note: Make sure the backend server is running on http://localhost:5000")

if __name__ == "__main__":
    test_waiver_wire_analysis()