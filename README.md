# POW Reminder MVP — Patient Visit Confirmation (Twilio + Jive)

A fast, HIPAA‑aware MVP that calls patients from your office caller ID to confirm appointments parsed directly from a Practice Fusion **“Schedule Confirmation view”** PDF. Patients can press:
- **1** to confirm,
- **2** to reschedule (warm‑transfer to your Jive/GoToConnect front desk),
- **3** to cancel,
- **9** to stop reminders.

The dashboard only targets rows where **CONFIRMATION = Not confirmed** and skips those already confirmed.


## Table of Contents
- [What this is](#what-this-is)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [One-time setup](#one-time-setup)
  - [Twilio](#twilio)
  - [Jive-GoToConnect](#jive-gotoconnect)
- [Local run](#local-run)
- [Using the app](#using-the-app)
- [Environment variables](#environment-variables)
- [Endpoints](#endpoints)
- [Troubleshooting](#troubleshooting)
- [Security & HIPAA notes](#security--hipaa-notes)
- [Project layout](#project-layout)
- [Roadmap (nice-to-haves)](#roadmap-nice-to-haves)
- [Contributing](#contributing)
- [License](#license)


## What this is
- **Goal:** Reduce no‑shows by automatically reminding patients and making it trivial to confirm or transfer to the front desk.
- **Input:** Practice Fusion export PDF (“Schedule Confirmation view”) containing columns: `PATIENT, TIME, PROVIDER, TYPE, CONFIRMATION`.
- **Output:** A real‑time dashboard that shows **Not confirmed** appointments and lets you **Call now** for each row. Calls run only within a configurable window (default **10:00–15:00** local time).


## Architecture
- **Backend:** Python 3.11+, FastAPI, Uvicorn, Twilio Python SDK
- **PDF parsing:** `pdfplumber` (or `pdfminer.six`) to read PF export
- **Views:** FastAPI + Jinja templates + vanilla JS
- **Telephony:** Twilio Programmable Voice for outbound calls, DTMF capture, and warm‑transfer to your **Jive/GoToConnect** DID
- **Tunneling:** `ngrok` exposes your local server via HTTPS so Twilio can reach your webhooks

High-level flow:
1. Upload PF PDF → parse rows where `CONFIRMATION = "Not confirmed"`.
2. Dashboard lists target appointments.
3. Click **Call now** → server starts a Twilio call from `TWILIO_FROM_NUMBER` to the patient.
4. IVR: “Press 1 to confirm, 2 to reschedule, 3 to cancel, 9 to stop reminders.”
   - 1/3/9 update status on the dashboard.
   - 2 performs a **warm transfer** to `JIVE_MAIN_NUMBER`.
5. If unanswered/voicemail, app plays the voicemail script. No recording is enabled.


## Prerequisites
- **Python 3.11+**
- **Twilio account** (Programmable Voice enabled)
- **Jive/GoToConnect** front‑desk DID (or the main office DID that rings humans)
- **ngrok** (free account is fine)
- (Recommended) **Virtual environment** for Python packages


## One-time setup

### Twilio
1. Log in to **Twilio Console**.
2. (If using PHI) Ensure your **BAA with Twilio** is in place before using real patient data.
3. Copy credentials: **Console → Account → General Settings → Account SID & Auth Token**.
4. Verify your **office caller ID** so calls show your real number:
   - **Console → Phone Numbers → Verified Caller IDs → Add**.
   - Twilio will call and read a 6‑digit code to your office line; enter it to verify.
   - Set this as `TWILIO_FROM_NUMBER`.
   - _Alternative:_ Buy a Twilio DID and use that as `TWILIO_FROM_NUMBER` for pilot.
5. Install **ngrok** and set your authtoken (from ngrok.com dashboard).

### Jive / GoToConnect
1. Log into **GoTo Admin (Jive)**.
2. Decide which DID to ring for reschedules (front desk or a scheduling queue).
3. Confirm it routes to **live humans** during your calling window (default 10:00–15:00).
4. Copy the 10‑digit DID (e.g., `+1412XXXXXXX`) for `JIVE_MAIN_NUMBER`.


## Local run

> Windows PowerShell commands are shown with `>` prompts; macOS/Linux with `$`.

1) **Clone/unzip** this repo somewhere easy (e.g., `Desktop/pow-reminder-mvp`).

2) **Create venv & install deps**
```bash
# macOS/Linux
$ cd pow-reminder-mvp/backend
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```
```powershell
# Windows (PowerShell)
> cd pow-reminder-mvp\backend
> py -3 -m venv .venv
> .\.venv\Scripts\Activate.ps1
> pip install -r requirements.txt
```

3) **Configure environment**
```bash
# Copy the example and fill it in
$ cp .env.example .env
# Edit .env with your values (see section below)
```

4) **Run the server**
```bash
# from pow-reminder-mvp/backend
$ uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

5) **Start ngrok** in another terminal
```bash
$ ngrok http 8000
```
Copy the HTTPS URL ngrok prints (e.g., `https://abc123.ngrok.io`) into `BASE_URL` in `.env`, then **restart uvicorn** so it picks up the change.

6) **Open the dashboard**  
Go to **http://localhost:8000**


## Using the app

1. **Upload a PF “Schedule Confirmation view” PDF** with the expected columns.
2. The app **skips rows** where `CONFIRMATION = Confirmed` and lists rows where `CONFIRMATION = Not confirmed`.
3. Click **Call now** for a row. For your **first test**, temporarily set the patient number to your cell.
4. Answer and try keys:
   - **1** Confirm → status updates to **Confirmed**.
   - **2** Reschedule → warm transfer to your `JIVE_MAIN_NUMBER`.
   - **3** Cancel → status updates to **Cancelled**.
   - **9** Stop → status updates to **Do Not Call**.
5. Let one call roll to **voicemail** and confirm the message is correct.
6. Calls only occur inside `CALL_WINDOW_START`–`CALL_WINDOW_END` (default 10:00–15:00).


## Environment variables

Create `backend/.env` from `.env.example` and set:

```ini
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1YOURJIVEDID       # or a Twilio number
JIVE_MAIN_NUMBER=+1YOURFRONTDESKDID
BASE_URL=https://YOUR-NGROK-SUBDOMAIN.ngrok.io
TIMEZONE=America/New_York
CALL_WINDOW_START=10:00
CALL_WINDOW_END=15:00
```

**Notes**
- `TWILIO_FROM_NUMBER` **must** be a verified caller ID or a purchased Twilio number.
- `BASE_URL` must match your current ngrok URL—ngrok free URLs change each time.
- `TIMEZONE` should be an IANA tz string (e.g., `America/New_York`).


## Endpoints

> Path prefixes may vary slightly depending on your routing, but the MVP ships with the following:

**UI**
- `GET /` — dashboard (upload form + table)

**App API**
- `POST /api/upload` — multipart PDF upload; parses appointments
- `GET /api/appointments` — JSON list of parsed appointments
- `POST /api/call/{appointment_id}` — triggers an outbound call
- `GET /healthz` — basic health check

**Twilio webhooks** (must be reachable at `BASE_URL`)
- `POST /twilio/voice` — returns the initial TwiML (greeting + <Gather>)
- `POST /twilio/gather` — handles DTMF results (1/2/3/9) and performs transfer
- `POST /twilio/status` — call status events for logging/metrics

**IVR Script (TwiML)**
- Greeting: “This is an appointment reminder from Prisk Orthopaedics and Wellness. Press 1 to confirm, 2 to reschedule, 3 to cancel, or 9 to stop reminders.”
- **1**: Mark confirmed; speak confirmation and hang up.
- **2**: Speak “Please hold while I connect you,” then `<Dial><Number>{JIVE_MAIN_NUMBER}</Number></Dial>`.
- **3**: Mark cancelled; speak acknowledgement and hang up.
- **9**: Mark do‑not‑call; speak acknowledgement and hang up.
- **No input**: Repeat menu once; then end with voicemail message if unanswered.


## Troubleshooting

- **21211 (Forbidden caller)**  
  Your `TWILIO_FROM_NUMBER` is not verified. Verify the Jive DID in **Twilio → Verified Caller IDs**, or switch to a Twilio number.

- **Twilio hits the wrong URL / nothing updates**  
  `BASE_URL` is stale. Update `.env` with your current ngrok URL and restart the server.

- **Voicemail mis‑detected / no answer**  
  Normal occasionally. The app still drops the voicemail; dashboard will show **Voicemail/No Answer**.

- **Warm transfer fails**  
  Ensure `JIVE_MAIN_NUMBER` rings a human during your call window and is a reachable DID (include `+1`).

- **Spam-likely labeling**  
  For pilots this is usually fine. If it’s bad, switch to a Twilio DID while we set up branded calling later.

- **PDF parsing missed a row**  
  The parser expects the PF headers shown above and common time/phone formats. Open an issue with a redacted sample and we’ll harden the regex.


## Security & HIPAA notes
- **No call recording** is enabled in the MVP (Pennsylvania is all‑party consent).
- Keep PHI minimal in prompts and logs. The voicemail message contains no specific medical details.
- Sign/confirm your **BAA with Twilio** before live patient traffic.
- Store PDFs only as long as needed; the MVP deletes uploads after parsing by default (verify in code).


## Project layout

```
pow-reminder-mvp/
├── backend/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── routes/
│   │   ├── calls.py            # Outbound call + webhook routing
│   │   └── uploads.py          # PDF upload endpoint
│   ├── services/
│   │   ├── pdf_parser.py       # Practice Fusion PDF → rows
│   │   └── twilio_client.py    # Twilio SDK wrapper
│   ├── templates/
│   │   └── index.html          # Dashboard UI (upload + table + actions)
│   ├── static/
│   │   └── app.js              # Minimal front-end interactivity
│   ├── models.py               # In-memory store / simple persistence
│   ├── settings.py             # Env vars & config
│   ├── requirements.txt
│   └── .env.example
├── samples/
│   └── pf_schedule_sample.pdf  # Optional sample for local testing (if included)
└── README.md
```


## Roadmap (nice-to-haves)
- ✅ Persistent DB (SQLite) + audit trail - COMPLETED
- Multi‑user auth with role‑based access
- Retry/backoff and batching (e.g., staggered call waves)
- Branded calling / CNAM improvements
- Practice Fusion API integration (replace PDF step)
- Spanish/translation detection and multilingual IVR
- Call outcome analytics and CSV export
- Windows service installation (run without console window)


## Contributing
1. Open an issue describing the change/bug.
2. Create a feature branch and submit a PR with clear description and testing notes.
3. For PHI, **never** attach real patient data. Use synthetic or redacted samples.


## License
MIT (or your preferred license). If this code will be closed-source, remove this section.
