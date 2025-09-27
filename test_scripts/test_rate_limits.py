#!/usr/bin/env python3
"""
Test script to verify rate limiting functionality
Tests both question and comment rate limiting
"""

import requests
import time
import json
from datetime import datetime

# Configuration from config.json
RATE_LIMIT_PER_IP = "3:30"  # 3 requests per 30 seconds per IP
RATE_LIMIT_GLOBAL = "30:5"   # 30 requests per 5 seconds globally

def test_rate_limiting():
    base_url = "http://localhost:5000"
    
    print("=" * 60)
    print("RATE LIMITING TEST")
    print("=" * 60)
    print(f"Config: {RATE_LIMIT_PER_IP} per IP, {RATE_LIMIT_GLOBAL} global")
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test 1: Normal question submission (should work)
    print("Test 1: Normal question submission")
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Test question 1"})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Normal question accepted")
    else:
        print(f"❌ Unexpected response: {response.text}")
    print()
    
    # Test 2: Rapid question submissions (should trigger rate limiting)
    print("Test 2: Rapid question submissions (testing per-IP rate limit)")
    print("Sending 5 questions rapidly...")
    
    for i in range(5):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Rapid test question {i+1}"})
        print(f"Question {i+1}: Status {response.status_code}", end="")
        
        if response.status_code == 429:
            print(" - ❌ BLOCKED (Rate limited)")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
        elif response.status_code == 200:
            print(" - ✅ Accepted")
        else:
            print(f" - ⚠️  Unexpected: {response.text}")
        
        time.sleep(0.1)  # Small delay between requests
    print()
    
    # Wait a bit before testing comments
    print("Waiting 2 seconds before testing comments...")
    time.sleep(2)
    
    # Test 3: Normal comment submission (should work)
    print("Test 3: Normal comment submission")
    response = requests.post(f"{base_url}/api/comments", 
                           json={"comment": "Test comment 1"})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Normal comment accepted")
    else:
        print(f"❌ Unexpected response: {response.text}")
    print()
    
    # Test 4: Rapid comment submissions (should trigger rate limiting)
    print("Test 4: Rapid comment submissions (testing per-IP rate limit)")
    print("Sending 5 comments rapidly...")
    
    for i in range(5):
        response = requests.post(f"{base_url}/api/comments", 
                               json={"comment": f"Rapid test comment {i+1}"})
        print(f"Comment {i+1}: Status {response.status_code}", end="")
        
        if response.status_code == 429:
            print(" - ❌ BLOCKED (Rate limited)")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
        elif response.status_code == 200:
            print(" - ✅ Accepted")
        else:
            print(f" - ⚠️  Unexpected: {response.text}")
        
        time.sleep(0.1)  # Small delay between requests
    print()
    
    # Test 5: Wait for rate limit to reset and test again
    print("Test 5: Waiting for rate limit reset (35 seconds)...")
    print("This will test if the rate limiting properly resets")
    for i in range(35):
        print(f"\rWaiting... {35-i} seconds remaining", end="", flush=True)
        time.sleep(1)
    print("\n")
    
    # Test after waiting
    print("Test 6: Testing after rate limit reset")
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Post-reset test question"})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Question accepted after rate limit reset")
    else:
        print(f"❌ Still blocked: {response.text}")
    
    response = requests.post(f"{base_url}/api/comments", 
                           json={"comment": "Post-reset test comment"})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Comment accepted after rate limit reset")
    else:
        print(f"❌ Still blocked: {response.text}")
    
    print()
    print("=" * 60)
    print("RATE LIMITING TEST COMPLETED")
    print("=" * 60)

def test_different_ips():
    """Test rate limiting with different IP addresses (simulated with headers)"""
    print("\n" + "=" * 60)
    print("TESTING RATE LIMITING WITH DIFFERENT IPs")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test with different X-Forwarded-For headers to simulate different IPs
    ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
    
    for i, ip in enumerate(ips):
        print(f"\nTesting with IP: {ip}")
        
        headers = {"X-Forwarded-For": ip}
        
        # Send 2 questions (should work)
        for j in range(2):
            response = requests.post(f"{base_url}/api/questions", 
                                   json={"question": f"Question from {ip} - {j+1}"},
                                   headers=headers)
            print(f"  Question {j+1}: Status {response.status_code}")
        
        # Send 2 comments (should work)
        for j in range(2):
            response = requests.post(f"{base_url}/api/comments", 
                                   json={"comment": f"Comment from {ip} - {j+1}"},
                                   headers=headers)
            print(f"  Comment {j+1}: Status {response.status_code}")
        
        time.sleep(0.5)  # Small delay between IP tests

if __name__ == "__main__":
    try:
        test_rate_limiting()
        test_different_ips()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:5000")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
