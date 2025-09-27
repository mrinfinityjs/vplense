#!/usr/bin/env python3
"""
Create demo data for Privacy Debate theme
"""

import requests
import time
import random

BASE_URL = "http://localhost:5000"

def add_demo_data():
    """Add demo data for privacy debate"""
    print("Creating Privacy Debate Demo Data...")
    
    # Topics for privacy debate
    topics = [
        "Data Privacy vs. Security",
        "Surveillance Capitalism", 
        "Government Surveillance",
        "Personal Data Ownership",
        "AI and Privacy",
        "Digital Rights",
        "Encryption and Privacy",
        "Social Media Privacy"
    ]
    
    # Questions for privacy debate
    questions = [
        "Should companies be allowed to collect and sell our personal data without explicit consent?",
        "Is government surveillance justified for national security purposes?",
        "How do we balance privacy rights with the benefits of AI and machine learning?",
        "Should we have a right to be forgotten online?",
        "Are end-to-end encryption apps a threat to national security?",
        "Should social media platforms be held accountable for data breaches?",
        "Is it ethical for employers to monitor employee communications?",
        "Should biometric data collection be regulated more strictly?",
        "Do we need stronger privacy laws in the digital age?",
        "Should tech companies be required to use privacy-by-design principles?"
    ]
    
    # Comments for privacy debate
    comments = [
        "Privacy is a fundamental human right that should be protected at all costs.",
        "I think some surveillance is necessary for security, but it needs strict oversight.",
        "The amount of data companies collect about us is terrifying.",
        "We've already given up too much privacy for convenience.",
        "AI can be beneficial, but we need strong privacy protections.",
        "The right to be forgotten should be universal, not just in the EU.",
        "Encryption is essential for protecting our digital communications.",
        "Social media platforms profit from our data - we should get a cut!",
        "Government surveillance has gone too far in recent years.",
        "We need to educate people about their digital rights.",
        "Privacy and security don't have to be mutually exclusive.",
        "The current data economy is fundamentally broken.",
        "Biometric data is too sensitive to be stored by private companies.",
        "We need stronger penalties for data breaches.",
        "Privacy should be the default, not an opt-in feature."
    ]
    
    # Add topics
    print("\nAdding topics...")
    for topic in topics:
        try:
            response = requests.post(f"{BASE_URL}/api/topics", json={"topic": topic})
            if response.status_code == 200:
                print(f"✓ Added topic: {topic}")
            else:
                print(f"✗ Failed to add topic: {topic}")
        except Exception as e:
            print(f"✗ Error adding topic {topic}: {e}")
        time.sleep(0.5)
    
    # Add questions (simulate different users)
    print("\nAdding questions...")
    for i, question in enumerate(questions):
        try:
            # Simulate different IP addresses
            headers = {'X-Forwarded-For': f'192.168.1.{100 + i}'}
            response = requests.post(f"{BASE_URL}/api/questions", 
                                   json={"question": question}, 
                                   headers=headers)
            if response.status_code == 200:
                print(f"✓ Added question: {question[:50]}...")
            else:
                print(f"✗ Failed to add question: {response.text}")
        except Exception as e:
            print(f"✗ Error adding question: {e}")
        time.sleep(1)  # Delay to avoid rate limiting
    
    # Add comments (simulate different users)
    print("\nAdding comments...")
    for i, comment in enumerate(comments):
        try:
            # Simulate different IP addresses
            headers = {'X-Forwarded-For': f'10.0.0.{50 + i}'}
            response = requests.post(f"{BASE_URL}/api/comments", 
                                   json={"comment": comment}, 
                                   headers=headers)
            if response.status_code == 200:
                print(f"✓ Added comment: {comment[:50]}...")
            else:
                print(f"✗ Failed to add comment: {response.text}")
        except Exception as e:
            print(f"✗ Error adding comment: {e}")
        time.sleep(1)  # Delay to avoid rate limiting
    
    print("\nDemo data creation completed!")
    print("\nYou can now demonstrate the system with privacy debate content.")

if __name__ == "__main__":
    add_demo_data()
