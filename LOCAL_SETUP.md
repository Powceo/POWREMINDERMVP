# POW Reminder - Local Office Setup Guide

This application runs entirely on your local Windows computer. No cloud services needed except for Twilio (for phone calls) and ngrok (for webhook connectivity).

## Quick Start (Windows)

### 1. First Time Setup
1. **Install Python 3.11** from https://www.python.org/downloads/
   - Check "Add Python to PATH" during installation

2. **Install ngrok** from https://ngrok.com/download
   - Just unzip to a folder like C:\ngrok
   - Add to Windows PATH for convenience

3. **Get Twilio Account** (one-time)
   - Sign up at https://www.twilio.com
   - Verify your office phone number (see detailed steps in SETUP_GUIDE.md)

### 2. Configure the Application
1. Navigate to `pow-reminder-mvp\backend` folder
2. Copy `.env.example` to `.env`
3. Edit `.env` with Notepad and add your credentials:
```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+14125551234  (your verified office number)
JIVE_MAIN_NUMBER=+14125559999    (your front desk number)
```

### 3. Daily Startup Process

**Step 1: Start the Application**
- Double-click `start_app.bat`
- Leave this window open all day
- The application is now running at http://localhost:8000

**Step 2: Start ngrok (for Twilio)**
- Double-click `start_ngrok.bat`
- Copy the HTTPS URL shown (like https://abc123.ngrok-free.app)
- Update BASE_URL in backend\.env with this URL
- Restart the application (close and reopen start_app.bat)

**Step 3: Access the Dashboard**
- Open Chrome/Edge
- Go to http://localhost:8000
- Bookmark this page

## Daily Workflow

### Morning Setup (8:00 AM)
1. Start both .bat files
2. Update ngrok URL in .env
3. Upload today's Practice Fusion PDF
4. System automatically shows only unconfirmed appointments

### During Call Window (10:00 AM - 3:00 PM)
- Click "Call Now" for each unconfirmed patient
- Monitor status updates in real-time
- Confirmed appointments disappear from the list
- Rescheduled patients transfer to front desk

### End of Day
- Close both command windows
- All data saved locally in `pow_reminder.db`
- Call history preserved for reports

## Data Storage

All data is stored locally in:
- **Database**: `backend\pow_reminder.db` (SQLite file)
- **Temporary PDFs**: Deleted after parsing
- **No cloud storage** - everything stays on this computer

### Backup Recommendation
- Copy `pow_reminder.db` to backup location weekly
- Located in: `pow-reminder-mvp\backend\pow_reminder.db`

## Troubleshooting

### "Cannot connect to server"
- Make sure `start_app.bat` is running
- Check Windows Firewall isn't blocking port 8000

### "Twilio webhooks failing"
- Ensure `start_ngrok.bat` is running
- Update BASE_URL in .env with current ngrok URL
- Restart the application

### "Outside call window" error
- Calls only work 10 AM - 3 PM by default
- Edit CALL_WINDOW times in .env if needed

### Application crashes
- Check `backend\logs` folder for errors
- Ensure Python 3.11 is installed
- Run `pip install -r requirements.txt` in backend folder

## Security Notes

### Local Security
- Application only accessible from this computer
- No external access without ngrok
- Database encrypted by Windows if BitLocker enabled

### HIPAA Considerations
- All data stays local (except voice calls via Twilio)
- No call recording enabled
- Sign BAA with Twilio for compliance
- Limit computer access to authorized staff

## Adding to Windows Startup (Optional)

To start automatically when Windows boots:
1. Press Win+R, type `shell:startup`
2. Create shortcuts to both .bat files
3. Place shortcuts in the Startup folder
4. Note: You'll still need to update ngrok URL daily

## Staff Training Points

1. **Upload PDF once per day** - Usually in the morning
2. **Only shows unconfirmed** - Confirmed patients filtered out
3. **Call during window** - 10 AM to 3 PM only
4. **One click to call** - Just press "Call Now"
5. **Status auto-updates** - Watch the dashboard
6. **Transfers work** - Press 2 sends to front desk

## Maintenance

### Weekly Tasks
- Backup `pow_reminder.db` file
- Check available disk space
- Review call success rates

### Monthly Tasks  
- Update Python packages: `pip install --upgrade -r requirements.txt`
- Clear old call logs if needed
- Review Twilio usage/costs

## Support Contacts

- **Twilio Issues**: https://support.twilio.com
- **Python Issues**: Check if Python properly installed
- **Database Location**: `backend\pow_reminder.db`
- **Logs Location**: Check console output in command windows

---

Remember: This runs entirely on your local computer. No patient data goes to the cloud except the voice calls through Twilio (which you'll have a BAA for).