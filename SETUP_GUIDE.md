# POW Reminder MVP - Complete Setup Guide

## Step-by-Step Twilio Account Setup

### 1. Create Twilio Account
1. Go to https://www.twilio.com/try-twilio
2. Sign up with your email
3. Verify your email address
4. Set up two-factor authentication (required)

### 2. Get Your Twilio Credentials
1. Log into Twilio Console: https://console.twilio.com
2. From the dashboard, copy:
   - **Account SID**: Starts with `AC` (34 characters)
   - **Auth Token**: Click the eye icon to reveal (32 characters)
3. Save these to your `.env` file

### 3. Verify Your Office Caller ID (IMPORTANT)
Since you want to use your Jive/GotoConnect office number as the caller ID:

1. In Twilio Console, go to **Phone Numbers** → **Manage** → **Verified Caller IDs**
2. Click **Add a new Caller ID**
3. Enter your office phone number (the one you want patients to see)
4. Select "Call Me" verification method
5. Twilio will call your office line with a 6-digit code
6. Enter the code in Twilio Console
7. Your office number is now verified and can be used as `TWILIO_FROM_NUMBER`

**Alternative Option - Buy a Twilio Number:**
1. Go to **Phone Numbers** → **Manage** → **Buy a number**
2. Search for a local number in your area code (412 for Pittsburgh)
3. Ensure it has "Voice" capabilities
4. Purchase for $1.15/month
5. Use this number as `TWILIO_FROM_NUMBER`

### 4. Enable Programmable Voice
1. In Console, go to **Voice** → **Settings**
2. Ensure "Programmable Voice" is enabled
3. No additional configuration needed for outbound calls

### 5. HIPAA Compliance (If Using Real Patient Data)
1. Go to **Account** → **Compliance**
2. Request a Business Associate Agreement (BAA)
3. Follow Twilio's HIPAA enablement process
4. Enable encryption at rest for your account

## Step-by-Step Jive/GotoConnect Setup

### 1. Identify Your Transfer Target Number
1. Log into GoTo Admin: https://admin.goto.com
2. Navigate to **Phone System** → **Users & Devices**
3. Find the appropriate destination:
   - **Option A - Direct User**: Find your front desk person's direct DID
   - **Option B - Ring Group**: Find the scheduling department ring group number
   - **Option C - Main Line**: Use your main office number

### 2. Verify the Number Routes Correctly
1. Test call the number from your cell phone
2. Confirm it reaches the right person/department
3. Verify someone answers during your call window hours (10am-3pm default)

### 3. Configure for Warm Transfer Compatibility
No special configuration needed on Jive side - the system will receive the transferred call like any other inbound call.

## Local Development Setup

### 1. Install Python and Dependencies
```bash
# Windows
> cd pow-reminder-mvp\backend
> py -3.11 -m venv .venv
> .\.venv\Scripts\Activate.ps1
> pip install -r requirements.txt

# Mac/Linux
$ cd pow-reminder-mvp/backend
$ python3.11 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
# Copy the example file
> copy .env.example .env  # Windows
$ cp .env.example .env    # Mac/Linux

# Edit .env with your actual values:
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+14125551234  # Your verified office number
JIVE_MAIN_NUMBER=+14125559999    # Your front desk/scheduling number
BASE_URL=https://your-ngrok-url.ngrok.io
TIMEZONE=America/New_York
CALL_WINDOW_START=10:00
CALL_WINDOW_END=15:00
```

### 3. Install and Configure ngrok
1. Download ngrok: https://ngrok.com/download
2. Sign up for free account: https://dashboard.ngrok.com/signup
3. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
4. Configure ngrok:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

### 4. Start the Application
```bash
# Terminal 1 - Start the FastAPI server
> cd pow-reminder-mvp\backend
> .\.venv\Scripts\Activate.ps1  # or source .venv/bin/activate
> uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Start ngrok tunnel
> ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
# Update BASE_URL in .env with this URL
# Restart the FastAPI server (Ctrl+C then run uvicorn again)
```

### 5. Access the Dashboard
Open your browser to: http://localhost:8000

## Testing Checklist

### Initial Test (Use Your Own Phone)
1. Upload the mock.pdf file
2. Edit one "Not confirmed" patient's phone to your cell number
3. Click "Call Now" for that patient
4. Answer and test each option:
   - Press 1: Confirm appointment
   - Press 2: Transfer to office
   - Press 3: Cancel
   - Press 9: Stop reminders
5. Let one call go to voicemail to test the voicemail message

### Production Readiness Checklist
- [ ] Twilio account funded ($20 minimum recommended)
- [ ] Office caller ID verified in Twilio
- [ ] Jive transfer number tested and working
- [ ] Call window times configured correctly
- [ ] Test with real PF PDF export
- [ ] Verify all phone numbers parse correctly
- [ ] Test during actual call window hours
- [ ] Confirm voicemail message is appropriate
- [ ] BAA signed with Twilio (for HIPAA)

## Troubleshooting

### Common Twilio Errors

**Error 21211 - Invalid 'To' Phone Number**
- Phone number format is incorrect
- Solution: Ensure all numbers include country code (+1 for US)

**Error 21214 - 'From' Phone Number Not Verified**
- Your office number isn't verified in Twilio
- Solution: Complete caller ID verification process above

**Error 21610 - Attempt to Call Unverified Number**
- Twilio trial accounts can only call verified numbers
- Solution: Upgrade account or verify test numbers first

### Common Setup Issues

**"Calls can only be made between X and Y"**
- You're outside the configured call window
- Solution: Adjust CALL_WINDOW_START/END in .env or wait

**PDF parsing finds 0 appointments**
- PDF format doesn't match expected PF export
- Solution: Ensure PDF is "Schedule Confirmation view" from Practice Fusion

**Warm transfer fails**
- JIVE_MAIN_NUMBER is incorrect or unreachable
- Solution: Verify the number format includes +1 and test it directly

**ngrok URL expires/changes**
- Free ngrok URLs change each restart
- Solution: Update BASE_URL in .env and restart server each time

## Cost Estimates

### Twilio Pricing (as of 2024)
- **Outbound calls**: $0.0085/minute
- **Toll-free numbers**: $0.013/minute (if using)
- **Phone number**: $1.15/month (if purchasing)
- **Estimated per patient**: ~$0.02-0.05 per confirmation call

### Example Monthly Costs
- 500 patients × $0.03 average = $15/month
- Plus phone number (if purchased) = $1.15/month
- **Total estimate**: ~$16-20/month for typical practice

## Security Best Practices

1. **Never commit .env file** - It's in .gitignore
2. **Rotate credentials regularly** - Especially Auth Token
3. **Use HTTPS only** - ngrok provides this automatically
4. **Limit call window** - Reduces potential for abuse
5. **Monitor usage** - Check Twilio console for unusual activity
6. **Implement rate limiting** - For production deployment
7. **Log access** - Track who uploads PDFs and initiates calls

## Next Steps

1. Complete all setup steps above
2. Test with mock data first
3. Run a pilot with 5-10 real appointments
4. Monitor and adjust IVR script as needed
5. Gradually increase usage
6. Consider production deployment (AWS/Azure/dedicated server)

## Support Resources

- **Twilio Support**: https://support.twilio.com
- **Twilio Status**: https://status.twilio.com
- **GoTo Support**: https://support.goto.com
- **ngrok Documentation**: https://ngrok.com/docs
- **Project Issues**: Create an issue in this repository

---

Remember to start small, test thoroughly, and gradually scale up your usage. Good luck with reducing no-shows!