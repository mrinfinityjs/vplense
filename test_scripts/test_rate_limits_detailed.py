#!/usr/bin/env python3
"""
Detailed rate limiting test to understand the blocking mechanism
"""

import requests
import time
import json
from datetime import datetime

def test_rate_limit_details():
    base_url = "http://localhost:5000"
    
    print("=" * 70)
    print("DETAILED RATE LIMITING ANALYSIS")
    print("=" * 70)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test the exact rate limit: 3 requests per 30 seconds
    print("Testing exact rate limit: 3 requests per 30 seconds")
    print("Sending exactly 3 questions...")
    
    for i in range(3):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Test question {i+1}"})
        print(f"Question {i+1}: Status {response.status_code}")
        if response.status_code == 200:
            print("  ✅ Accepted")
        else:
            print(f"  ❌ Blocked: {response.json().get('error', 'Unknown')}")
        time.sleep(0.5)
    
    print("\nNow testing the 4th request (should be blocked):")
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Question 4 - should be blocked"})
    print(f"Question 4: Status {response.status_code}")
    if response.status_code == 429:
        print("  ❌ BLOCKED (Rate limited) - This is expected!")
        print(f"  Error: {response.json().get('error', 'Unknown')}")
    else:
        print("  ⚠️  Unexpected - should have been blocked")
    
    print("\n" + "="*50)
    print("TESTING BLOCK DURATION")
    print("="*50)
    print("The IP should be blocked for 120 seconds according to config")
    print("Testing if we can still make requests after being blocked...")
    
    # Test immediately after blocking
    print("\nImmediate test (should be blocked):")
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Immediate test"})
    print(f"Status: {response.status_code} - {response.json().get('error', 'Success')}")
    
    # Test after 5 seconds
    print("\nWaiting 5 seconds...")
    time.sleep(5)
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "After 5 seconds"})
    print(f"Status: {response.status_code} - {response.json().get('error', 'Success')}")
    
    # Test after 10 seconds
    print("\nWaiting another 5 seconds (10 total)...")
    time.sleep(5)
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "After 10 seconds"})
    print(f"Status: {response.status_code} - {response.json().get('error', 'Success')}")
    
    print("\n" + "="*50)
    print("TESTING WITH FRESH IP")
    print("="*50)
    print("Testing with a different IP to see if rate limiting is per-IP...")
    
    headers = {"X-Forwarded-For": "10.0.0.100"}
    
    for i in range(3):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Fresh IP question {i+1}"},
                               headers=headers)
        print(f"Fresh IP Question {i+1}: Status {response.status_code}")
        if response.status_code == 200:
            print("  ✅ Accepted")
        else:
            print(f"  ❌ Blocked: {response.json().get('error', 'Unknown')}")
        time.sleep(0.5)
    
    # Test 4th request with fresh IP
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Fresh IP question 4"},
                           headers=headers)
    print(f"Fresh IP Question 4: Status {response.status_code}")
    if response.status_code == 429:
        print("  ❌ BLOCKED - Rate limiting works per IP!")
    else:
        print("  ⚠️  Unexpected - should have been blocked")

def test_global_rate_limit():
    """Test if there's a global rate limit affecting all IPs"""
    print("\n" + "="*70)
    print("TESTING GLOBAL RATE LIMIT")
    print("="*70)
    print("Config shows: 30 requests per 5 seconds globally")
    print("This should affect ALL IPs combined")
    
    base_url = "http://localhost:5000"
    
    # Test with multiple IPs sending requests rapidly
    ips = [f"192.168.1.{100+i}" for i in range(10)]  # 10 different IPs
    
    print(f"Sending requests from {len(ips)} different IPs...")
    
    success_count = 0
    blocked_count = 0
    
    for i, ip in enumerate(ips):
        headers = {"X-Forwarded-For": ip}
        
        for j in range(4):  # 4 requests per IP = 40 total requests
            response = requests.post(f"{base_url}/api/questions", 
                                   json={"question": f"Global test {i}-{j}"},
                                   headers=headers)
            
            if response.status_code == 200:
                success_count += 1
                print(f"✅ {ip} request {j+1}: Accepted")
            elif response.status_code == 429:
                blocked_count += 1
                error = response.json().get('error', 'Unknown')
                print(f"❌ {ip} request {j+1}: BLOCKED - {error}")
            else:
                print(f"⚠️  {ip} request {j+1}: Status {response.status_code}")
            
            time.sleep(0.05)  # Very small delay
    
    print(f"\nResults:")
    print(f"  Total requests: {success_count + blocked_count}")
    print(f"  Successful: {success_count}")
    print(f"  Blocked: {blocked_count}")
    
    if blocked_count > 0:
        print("✅ Global rate limiting is working!")
    else:
        print("⚠️  No global rate limiting detected")

if __name__ == "__main__":
    try:
        test_rate_limit_details()
        test_global_rate_limit()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:5000")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
