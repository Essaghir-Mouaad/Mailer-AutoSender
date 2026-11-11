#!/usr/bin/env python3
"""Send the next N emails from a CSV list each time it runs.

Progress is saved in sent.csv, so each run continues where the last stopped.
Usage:
    python3 send_daily.py --dry-run     # test, nothing is sent
    python3 send_daily.py               # send the next batch
"""
import argparse
import csv
import random
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

from mail_config import load_mail_credentials

BASE = Path(__file__).parent
LIST_FILE = BASE / "emails_clean.csv"  # created by clean_list.py
BOUNCED_FILE = BASE / "bounced.csv"
SENT_FILE = BASE / "sent.csv"
SUBJECT_FILE = BASE / "subject.txt"
BODY_FILE = BASE / "body.txt"
ATTACHMENT = BASE / "CV_Mouaad_Essaghir.pdf"

BATCH_SIZE = 10
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def load_list():
    with open(LIST_FILE, newline="", encoding="utf-8") as f:
        rows = [r["Email"].strip().lower() for r in csv.DictReader(f) if r.get("Email")]
    seen, unique = set(), []
    for e in rows:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def load_sent():
    if not SENT_FILE.exists():
        return set()
    with open(SENT_FILE, newline="", encoding="utf-8") as f:
        return {r[0] for r in csv.reader(f) if r}


def log_sent(email, status):
    with open(SENT_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([email, status, time.strftime("%Y-%m-%d %H:%M:%S")])


def build_message(sender, to, subject, body):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg["List-Unsubscribe"] = f"<mailto:{sender}?subject=unsubscribe>"
    msg.set_content(body)
    if ATTACHMENT.exists():
        msg.add_attachment(
            ATTACHMENT.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=ATTACHMENT.name,
        )
    return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sender, password = load_mail_credentials()
    if not args.dry_run and not (sender and password):
        raise SystemExit("Set MAIL_USER and MAIL_APP_PASSWORD in .env.")

    subject = SUBJECT_FILE.read_text(encoding="utf-8").strip()
    body = BODY_FILE.read_text(encoding="utf-8")

    if not LIST_FILE.exists():
        raise SystemExit("Run clean_list.py first (it creates emails_clean.csv).")
    already = load_sent()
    if BOUNCED_FILE.exists():
        with open(BOUNCED_FILE, newline="", encoding="utf-8") as f:
            already |= {r[0].strip().lower() for r in csv.reader(f) if r}
    todo = [e for e in load_list() if e not in already][:BATCH_SIZE]
    print(f"{len(todo)} emails in this batch")
    if not todo:
        print("List finished.")
        return

    if args.dry_run:
        for e in todo:
            print("would send to", e)
        return

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
        server.login(sender, password)
        for e in todo:
            try:
                server.send_message(build_message(sender, e, subject, body))
                log_sent(e, "ok")
                print("sent", e)
            except Exception as exc:  # keep going, record the failure
                log_sent(e, f"error: {exc}")
                print("failed", e, exc)
            time.sleep(random.uniform(100, 130))  # spread sends out


if __name__ == "__main__":
    main()
