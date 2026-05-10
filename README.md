# Echo Protocol — Dead Man's Switch System
⚠️Entire project needs to be tested before usage.This is a version 1.
Before the actual project.Below is a description of what this project tries to achieve.
Echo Protocol is a self-hosted dead man's switch system built for people who understand that security and privacy don't come from trusting the right company — they come from eliminating trust requirements entirely.
Most dead man's switch tools ask you to hand your secrets to a third party, rely on a single trigger mechanism, and hope the service stays online and honest indefinitely. Echo Protocol takes the opposite approach. Your data stays on your infrastructure, encrypted, under your control. No company has access to it. No single point of failure can expose it or falsely release it.
The system monitors up to 10 independent activity signals simultaneously — email, GPS location, physical USB hardware, browser behavior, financial activity, smart home sensors, server heartbeats, social media, calendar events, and daily check-ins. It only fires when a configurable number of these signals fail at the same time. This M-of-N consensus logic is what separates it from every popular alternative — losing your phone won't trigger it, going on vacation won't trigger it, forgetting to check an email for a week won't trigger it. It fires when the pattern of silence across independent, unrelated systems suggests something is genuinely wrong.
For the right person, this solves a real problem that no commercial tool adequately addresses. Journalists protecting source documents. Security researchers holding sensitive disclosures. People with significant cryptocurrency holdings and no institutional safety net. Solo founders with critical infrastructure credentials. Anyone who needs a trusted automated system to reach people on their behalf if they become unreachable — without compromising their security to build it.
It is the most architecturally sound approach to this problem available as an open implementation. The ceiling it offers — zero third-party knowledge, multi-signal consensus, hardware token support, fully encrypted payloads, no subscription dependency — is genuinely higher than any commercially available alternative. Whether someone reaches that ceiling depends on how carefully they deploy it, but the capability is there.
It's a tool built for people who have something worth protecting and the technical means to protect it properly.
.........................................................................................................................................................

A comprehensive, self-hosted dead man's switch with **10 independent trigger mechanisms** and **M-of-N consensus logic** to prevent false positives.

## How It Works

The system only fires when **M or more** of your configured triggers detect inactivity simultaneously. For example, with M=3, losing your phone (GPS), forgetting email, *and* missing a daily streak would be required to fire — any one alone won't trigger it.

## Trigger Types

| Key | Description | Default Threshold |
|-----|-------------|-------------------|
| `email_inactivity` | Gmail sent-folder inactivity | 90 days |
| `gps_safe_zone` | Device outside safe zone | 24 hours |
| `daily_streak` | Daily check-in button | 3 days missed |
| `financial_stagnation` | No outbound bank/crypto tx | 30 days |
| `usb_token` | USB key not present | 7 days |
| `social_media` | No GitHub/Reddit activity | 30 days |
| `smart_home` | No motion sensor activity | 48 hours |
| `calendar_checkin` | Calendar event not completed | 7 days |
| `dns_heartbeat` | Server heartbeat stopped | 24 hours |
| `browser_activity` | No browser interaction | 7 days |

## Quick Start

```bash
# 1. Clone and set up
cd echoprotocol
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set API_SECRET_KEY

# 3. Generate an encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste output as ENCRYPTION_KEY in .env

# 4. Run
python main.py
```

Dashboard: http://localhost:5000

## Configure via API

```bash
export KEY="your-api-secret-key"   # from .env

# Add a daily streak trigger
curl -X POST http://localhost:5000/api/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"name":"Daily Check-In","type":"daily_streak","threshold_seconds":259200}'

# Add a DNS heartbeat trigger
curl -X POST http://localhost:5000/api/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"name":"Server Heartbeat","type":"dns_heartbeat","threshold_seconds":86400}'

# Add an emergency contact
curl -X POST http://localhost:5000/api/contacts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"name":"Alice","email":"alice@example.com","phone":"+1234567890","priority":1}'

# Add a payload message
curl -X POST http://localhost:5000/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"name":"My Message","type":"message","content":"If you received this..."}'
```

## Daily Check-In

```bash
# Check in on trigger ID 1 (no auth required for activity endpoints)
curl -X POST http://localhost:5000/api/triggers/1/activity

# DNS heartbeat from a server
curl -X POST http://localhost:5000/api/triggers/2/activity \
  -H "Content-Type: application/json" \
  -d '{"device_id":"home-server"}'
```

## Browser Extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `browser_extension/` folder
4. Edit `background.js` to set your `TRIGGER_ID`

## GPS Reporter (Android/Termux)

```bash
pkg install termux-api python
pip install requests
# Edit ECHO_API_URL and TRIGGER_ID in mobile/gps_reporter.py
python mobile/gps_reporter.py
```

## Production Notes

- Use HTTPS + a reverse proxy (nginx/Caddy) in production
- Set a strong, random `API_SECRET_KEY`
- Enable database backups (`data/echo.db`)
- Monitor the Echo Protocol server itself (ironic but necessary)
- Use a proper secrets manager for credentials
