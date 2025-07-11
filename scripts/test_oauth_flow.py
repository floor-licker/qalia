#!/usr/bin/env python3
"""
OAuth Flow Test Script

This script helps debug OAuth flow issues by simulating the OAuth callback
and testing session management.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your server URL
# BASE_URL = "http://157.245.241.244"  # Production URL

def test_oauth_flow():
    """Test the OAuth flow and session management"""
    
    print("🔍 Testing OAuth Flow")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Auth Check (unauthenticated)
    print("\n2. Testing Auth Check (should be unauthenticated)...")
    try:
        response = requests.get(f"{BASE_URL}/api/auth/user")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: OAuth Login URL
    print("\n3. Testing OAuth Login URL Generation...")
    try:
        response = requests.get(f"{BASE_URL}/api/auth/login")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Response: {data}")
        
        if "auth_url" in data:
            print(f"   Auth URL: {data['auth_url'][:100]}...")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Debug Auth Endpoint
    print("\n4. Testing Debug Auth Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/debug/auth")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Debug Info:")
        print(f"   - Timestamp: {data.get('timestamp')}")
        print(f"   - Cookies: {data.get('cookies', {})}")
        print(f"   - Session: {data.get('session', {})}")
        print(f"   - Server State: {data.get('server_state', {})}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Session with Manual Cookie
    print("\n5. Testing Session with Manual Cookie...")
    print("   (This would require a real session ID from OAuth flow)")
    
    print("\n" + "=" * 50)
    print("✅ OAuth Flow Test Complete")
    print("\nNext steps:")
    print("1. Run this script before OAuth flow")
    print("2. Complete OAuth flow manually in browser")
    print("3. Run this script again to see session state")
    print("4. Check server logs for detailed OAuth flow")

if __name__ == "__main__":
    test_oauth_flow() 