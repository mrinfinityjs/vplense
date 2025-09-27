#!/usr/bin/env python3
"""
Test script for excessive rate limiting functionality
Tests: "rate_limit_excessive": "5:60", "rate_limit_excessive_block_for": "600"
"""

import requests
import time
import json
from datetime import datetime

def test_excessive_rate_limiting():
    base_url = "http://localhost:5000"
    
    print("=" * 80)
    print("EXCESSIVE RATE LIMITING TEST")
    print("=" * 80)
    print("Config: 5 rate limit hits in 60 seconds triggers 600 second block")
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test 1: Trigger normal rate limiting multiple times to reach excessive threshold
    print("Test 1: Triggering rate limits to reach excessive threshold")
    print("Need to trigger rate limiting 5 times in 60 seconds...")
    
    headers = {"X-Forwarded-For": "192.168.100.50"}
    
    for attempt in range(5):
        print(f"\nAttempt {attempt + 1}/5: Triggering rate limit...")
        
        # Send 4 requests rapidly to trigger rate limit (limit is 3 per 30 seconds)
        for i in range(4):
            response = requests.post(f"{base_url}/api/questions", 
                                   json={"question": f"Excessive test {attempt}-{i}"},
                                   headers=headers)
            print(f"  Request {i+1}: Status {response.status_code}", end="")
            
            if response.status_code == 429:
                print(" - ❌ BLOCKED (Rate limited)")
                try:
                    error_data = response.json()
                    print(f"    Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"    Response: {response.text}")
            elif response.status_code == 200:
                print(" - ✅ Accepted")
            else:
                print(f" - ⚠️  Unexpected: {response.text}")
            
            time.sleep(0.1)
        
        # Wait a bit before next attempt to allow some reset
        if attempt < 4:
            print(f"  Waiting 15 seconds before next attempt...")
            time.sleep(15)
    
    print("\n" + "="*60)
    print("CHECKING IF EXCESSIVE RATE LIMITING WAS TRIGGERED")
    print("="*60)
    
    # Test if the IP is now excessively blocked
    print("Testing if IP is now excessively blocked (should be blocked for 600 seconds)...")
    
    for i in range(3):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Excessive block test {i}"},
                               headers=headers)
        print(f"Request {i+1}: Status {response.status_code}", end="")
        
        if response.status_code == 429:
            print(" - ❌ BLOCKED")
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                print(f"    Error: {error_msg}")
                
                if "excessive" in error_msg.lower():
                    print("    ✅ EXCESSIVE RATE LIMITING DETECTED!")
                elif "temporarily blocked" in error_msg.lower():
                    print("    ⚠️  IP is blocked but may not be excessive block")
            except:
                print(f"    Response: {response.text}")
        elif response.status_code == 200:
            print(" - ✅ Accepted (Not excessively blocked)")
        else:
            print(f" - ⚠️  Unexpected: {response.text}")
        
        time.sleep(1)
    
    print("\n" + "="*60)
    print("TESTING WITH FRESH IP")
    print("="*60)
    print("Testing with a different IP to verify excessive blocking is per-IP...")
    
    fresh_headers = {"X-Forwarded-For": "192.168.100.51"}
    
    for i in range(3):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Fresh IP test {i}"},
                               headers=fresh_headers)
        print(f"Fresh IP Request {i+1}: Status {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Accepted - Fresh IP not affected by excessive blocking")
        elif response.status_code == 429:
            print("  ❌ Blocked - May be global rate limiting")
        else:
            print(f"  ⚠️  Unexpected: {response.text}")
        
        time.sleep(0.5)
    
    print("\n" + "="*80)
    print("EXCESSIVE RATE LIMITING TEST COMPLETED")
    print("="*80)
    print("Note: If excessive rate limiting is working, the IP should be blocked for 10 minutes")
    print("Check the server logs for excessive rate limit notifications")

def test_rate_limit_notifications():
    """Test if rate limit notifications are being sent to admins"""
    print("\n" + "="*80)
    print("TESTING RATE LIMIT NOTIFICATIONS")
    print("="*80)
    print("This test will trigger rate limits and check if notifications are sent")
    
    base_url = "http://localhost:5000"
    
    # First, login as admin to receive notifications
    print("Logging in as admin...")
    login_response = requests.post(f"{base_url}/api/admin/login", 
                                 json={"password": "admin"})
    
    if login_response.status_code == 200:
        print("✅ Admin login successful")
        session_cookies = login_response.cookies
        
        # Now trigger rate limiting
        print("\nTriggering rate limiting...")
        headers = {"X-Forwarded-For": "192.168.100.60"}
        
        for i in range(4):  # 4 requests to trigger rate limit
            response = requests.post(f"{base_url}/api/questions", 
                                   json={"question": f"Notification test {i}"},
                                   headers=headers)
            print(f"Request {i+1}: Status {response.status_code}")
            time.sleep(0.1)
        
        print("\nRate limiting triggered. Check the Live Feed for notifications.")
        print("You should see rate limit notifications in the admin interface.")
        
    else:
        print("❌ Admin login failed")

if __name__ == "__main__":
    try:
        test_excessive_rate_limiting()
        test_rate_limit_notifications()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:5000")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
