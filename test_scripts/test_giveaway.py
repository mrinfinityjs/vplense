#!/usr/bin/env python3
"""
Test script for the giveaway system
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_giveaway_system():
    """Test the giveaway system functionality"""
    print("Testing Giveaway System...")
    
    # Test 1: Create a giveaway
    print("\n1. Creating a giveaway...")
    giveaway_data = {
        "name": "Test Giveaway",
        "delay_minutes": 0,  # Start immediately
        "recurring": False,
        "recurring_interval": 0,
        "remove_on_accept": True
    }
    
    response = requests.post(f"{BASE_URL}/api/giveaways", json=giveaway_data)
    if response.status_code == 200:
        giveaway = response.json()
        print(f"✓ Giveaway created: {giveaway['name']} (ID: {giveaway['id']})")
        giveaway_id = giveaway['id']
    else:
        print(f"✗ Failed to create giveaway: {response.text}")
        return
    
    # Test 2: Add items to the giveaway
    print("\n2. Adding items to giveaway...")
    items = [
        {"name": "Test Item 1", "link": "https://example.com/item1"},
        {"name": "Test Item 2", "link": "https://example.com/item2"},
        {"name": "Test Item 3", "link": "https://example.com/item3"}
    ]
    
    for item in items:
        response = requests.post(f"{BASE_URL}/api/giveaways/{giveaway_id}/items", json=item)
        if response.status_code == 200:
            print(f"✓ Item added: {item['name']}")
        else:
            print(f"✗ Failed to add item: {response.text}")
    
    # Test 3: Get all giveaways
    print("\n3. Getting all giveaways...")
    response = requests.get(f"{BASE_URL}/api/giveaways")
    if response.status_code == 200:
        giveaways = response.json()
        print(f"✓ Found {len(giveaways)} giveaways")
        for g in giveaways:
            print(f"  - {g['name']} ({len(g['items'])} items)")
    else:
        print(f"✗ Failed to get giveaways: {response.text}")
    
    # Test 4: Test winner selection (this would require a connected client)
    print("\n4. Testing winner selection...")
    print("Note: Winner selection requires connected clients. This test would need a real client connection.")
    
    # Test 5: Clean up - delete the giveaway
    print("\n5. Cleaning up...")
    response = requests.delete(f"{BASE_URL}/api/giveaways/{giveaway_id}")
    if response.status_code == 200:
        print("✓ Giveaway deleted")
    else:
        print(f"✗ Failed to delete giveaway: {response.text}")
    
    print("\nGiveaway system test completed!")

if __name__ == "__main__":
    test_giveaway_system()
