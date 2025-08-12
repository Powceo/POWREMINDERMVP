from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
if not env_path.exists():
    # Try current directory
    env_path = Path.cwd() / '.env'
    
print(f"Looking for .env at: {env_path}")
load_dotenv(env_path)

def make_test_call():
    """Make a test call with inline TwiML instead of webhooks"""
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    
    print(f"Account SID: {account_sid[:10]}..." if account_sid else "Account SID: NOT FOUND")
    print(f"Auth Token: {auth_token[:10]}..." if auth_token else "Auth Token: NOT FOUND")
    print(f"From Number: {from_number}" if from_number else "From Number: NOT FOUND")
    
    if not all([account_sid, auth_token, from_number]):
        print("\nMissing Twilio credentials!")
        print("Make sure your .env file is in the backend directory")
        print(f"Current directory: {os.getcwd()}")
        return
    
    client = Client(account_sid, auth_token)
    
    # Create TwiML directly
    response = VoiceResponse()
    response.say("This is a test from Prisk Orthopaedics and Wellness.", voice="alice")
    gather = response.gather(num_digits=1, action="http://demo.twilio.com/docs/voice.xml", method="POST")
    gather.say("Press 1 to confirm your appointment, or press 2 to speak with someone.")
    response.say("We didn't receive your selection. Goodbye.")
    
    twiml = str(response)
    
    # Make the call with inline TwiML
    to_number = input("Enter phone number to call (format: +14125551234): ")
    
    try:
        call = client.calls.create(
            to=to_number,
            from_=from_number,
            twiml=twiml
        )
        print(f"Call initiated! Call SID: {call.sid}")
        print("Check your phone!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    make_test_call()