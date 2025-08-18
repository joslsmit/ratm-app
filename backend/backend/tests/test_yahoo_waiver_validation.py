#!/usr/bin/env python3
"""
Test script for Yahoo waiver wire endpoint parameter validation
"""

import requests
import json
import sys

def test_endpoint_validation():
    """Test the Yahoo waiver wire endpoint parameter validation."""
    base_url = "http://localhost:5000"
    
    print("🔍 Testing Yahoo Waiver Wire Endpoint Parameter Validation")
    print("=" * 60)
    
    # Test 1: Missing league_key parameter (should return 400)
    print("\n📋 Test 1: Missing league_key parameter")
    try:
        response = requests.get(f"{base_url}/api/yahoo/waiver_wire", 
                               headers={"Content-Type": "application/json"},
                               timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ PASS: Correctly returned 400 for missing league_key")
        else:
            print("❌ FAIL: Expected 400 status code")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Connection error - {e}")
        print("💡 Make sure backend server is running on localhost:5000")
        return
    
    # Test 2: Missing Authorization header (should return 401)
    print("\n📋 Test 2: Missing Authorization header")
    try:
        response = requests.get(f"{base_url}/api/yahoo/waiver_wire?league_key=test.l.12345", 
                               headers={"Content-Type": "application/json"},
                               timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 401:
            print("✅ PASS: Correctly returned 401 for missing Authorization")
        else:
            print("❌ FAIL: Expected 401 status code")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Connection error - {e}")
        return
    
    # Test 3: Valid parameters (should return 200 with test message)
    print("\n📋 Test 3: Valid parameters")
    try:
        response = requests.get(f"{base_url}/api/yahoo/waiver_wire?league_key=test.l.12345", 
                               headers={
                                   "Content-Type": "application/json",
                                   "Authorization": "Bearer test_token_123"
                               },
                               timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if "league_key" in data and data["league_key"] == "test.l.12345":
                print("✅ PASS: Correctly processed valid parameters")
            else:
                print("❌ FAIL: Response missing expected data")
        else:
            print("❌ FAIL: Expected 200 status code")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Connection error - {e}")
        return
    
    print("\n🎉 Parameter validation testing complete!")
    print("💡 If all tests passed, endpoint foundation is working correctly")

if __name__ == "__main__":
    test_endpoint_validation()