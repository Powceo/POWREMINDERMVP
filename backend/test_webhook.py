import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

BASE_URL = os.getenv("BASE_URL", "")

print(f"Testing webhooks with BASE_URL: {BASE_URL}")
print("-" * 50)

if not BASE_URL or BASE_URL == "http://localhost:8000":
    print("ERROR: BASE_URL is not set to a public URL")
    print("You need a tunnel (ngrok, localhost.run, etc.) for webhooks to work")
else:
    # Test if the URL is reachable
    test_urls = [
        f"{BASE_URL}/healthz",
        f"{BASE_URL}/twilio/voice",
        f"{BASE_URL}/twilio/gather"
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        try:
            # Test GET first (won't work for POST endpoints but shows connectivity)
            response = requests.get(url, timeout=5)
            print(f"  GET Response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: {e}")
        
        # Test POST for webhook endpoints
        if "/twilio/" in url:
            try:
                # Simulate Twilio webhook data
                data = {
                    "CallSid": "TEST123",
                    "From": "+14125551234",
                    "To": "+14125557692",
                    "CallStatus": "in-progress"
                }
                if "gather" in url:
                    data["Digits"] = "1"
                
                response = requests.post(url, data=data, timeout=5)
                print(f"  POST Response: {response.status_code}")
                if response.status_code == 200:
                    print(f"  Response preview: {response.text[:200]}...")
            except requests.exceptions.RequestException as e:
                print(f"  POST ERROR: {e}")

print("\n" + "-" * 50)
print("Summary:")
if "localhost.run" in BASE_URL:
    print("✓ Using localhost.run tunnel")
elif "ngrok" in BASE_URL:
    print("✓ Using ngrok tunnel")
else:
    print("⚠ Using unknown tunnel/URL - make sure it's publicly accessible")

print(f"\nIf webhooks aren't working:")
print("1. Make sure your tunnel is running")
print("2. Make sure BASE_URL in .env matches the tunnel URL")
print("3. Check Twilio Console for error logs")
print("4. Make sure the app is running on port 800")