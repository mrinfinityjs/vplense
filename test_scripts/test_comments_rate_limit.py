#!/usr/bin/env python3
"""
Test rate limiting specifically for comments
"""

import requests
import time
import json
from datetime import datetime

def test_comment_rate_limiting():
    base_url = "http://localhost:5000"
    
    print("=" * 70)
    print("COMMENT RATE LIMITING TEST")
    print("=" * 70)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test comment rate limiting with fresh IP
    print("Testing comment rate limiting with fresh IP...")
    headers = {"X-Forwarded-For": "172.16.0.50"}
    
    print("Sending 4 comments rapidly (limit is 3 per 30 seconds)...")
    
    for i in range(4):
        response = requests.post(f"{base_url}/api/comments", 
                               json={"comment": f"Test comment {i+1}"},
                               headers=headers)
        print(f"Comment {i+1}: Status {response.status_code}", end="")
        
        if response.status_code == 200:
            print(" - ✅ Accepted")
        elif response.status_code == 429:
            print(" - ❌ BLOCKED (Rate limited)")
            try:
                error_data = response.json()
                print(f"    Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"    Response: {response.text}")
        else:
            print(f" - ⚠️  Unexpected: {response.text}")
        
        time.sleep(0.1)  # Small delay between requests
    
    print("\n" + "="*50)
    print("TESTING MIXED QUESTION AND COMMENT RATE LIMITING")
    print("="*50)
    print("Testing if questions and comments share the same rate limit...")
    
    headers = {"X-Forwarded-For": "172.16.0.60"}
    
    # Send 2 questions
    print("Sending 2 questions...")
    for i in range(2):
        response = requests.post(f"{base_url}/api/questions", 
                               json={"question": f"Mixed test question {i+1}"},
                               headers=headers)
        print(f"  Question {i+1}: Status {response.status_code}")
        time.sleep(0.1)
    
    # Send 2 comments
    print("Sending 2 comments...")
    for i in range(2):
        response = requests.post(f"{base_url}/api/comments", 
                               json={"comment": f"Mixed test comment {i+1}"},
                               headers=headers)
        print(f"  Comment {i+1}: Status {response.status_code}")
        time.sleep(0.1)
    
    # Try one more of each (should be blocked if they share rate limit)
    print("\nTrying additional requests...")
    
    response = requests.post(f"{base_url}/api/questions", 
                           json={"question": "Additional question"},
                           headers=headers)
    print(f"Additional question: Status {response.status_code}")
    
    response = requests.post(f"{base_url}/api/comments", 
                           json={"comment": "Additional comment"},
                           headers=headers)
    print(f"Additional comment: Status {response.status_code}")

if __name__ == "__main__":
    try:
        test_comment_rate_limiting()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:5000")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
