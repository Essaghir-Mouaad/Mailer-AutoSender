#!/usr/bin/env python3
"""Read Gmail bounce messages and record the failed addresses in bounced.csv,
so the sender never retries them and you can see your real bounce rate.

Run it each morning (before send_daily.py):
    python3 check_bounces.py
"""
import csv
import email
import imaplib
import re
from datetime import date, timedelta
from pathlib import Path

from mail_config import load_mail_credentials

BASE = Path(__file__).parent
BOUNCED = BASE / "bounced.csv"
DAYS_BACK = 3

user, pwd = load_mail_credentials()
if not (user and pwd):
    raise SystemExit("Set MAIL_USER and MAIL_APP_PASSWORD in .env.")

known = set()
if BOUNCED.exists():
    with open(BOUNCED, newline="", encoding="utf-8") as f:
        known = {r[0] for r in csv.reader(f) if r}

M = imaplib.IMAP4_SSL("imap.gmail.com")
M.login(user, pwd)
M.select("INBOX")
since = (date.today() - timedelta(days=DAYS_BACK)).strftime("%d-%b-%Y")
_, data = M.search(None, f'(FROM "mailer-daemon" SINCE {since})')

EMAIL_RX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
new = []
for num in data[0].split():
    _, msg_data = M.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    failed = msg.get("X-Failed-Recipients")
    addrs = []
    if failed:
        addrs = [a.strip().lower() for a in failed.split(",")]
    else:
        text = ""
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "message/delivery-status"):
                payload = part.get_payload(decode=True)
                if payload:
                    text += payload.decode("utf-8", "ignore")
        m = re.search(r"(?:delivered to|message to)\s+(" + EMAIL_RX.pattern + ")", text)
        if m:
            addrs = [m.group(1).lower()]
    for a in addrs:
        if a and a != user.lower() and a not in known:
            known.add(a)
            new.append(a)
M.logout()

with open(BOUNCED, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for a in new:
        w.writerow([a])

print(f"{len(new)} new bounced addresses recorded ({len(known)} total).")
