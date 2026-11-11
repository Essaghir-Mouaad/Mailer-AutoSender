# Daily Mailer

A small Python tool that sends a batch of emails (default: **50 per day**) from a CSV list through your Gmail account. It was built for sending spontaneous job or internship applications with a CV attached, but it works for any personal outreach you are entitled to send.

It runs on Ubuntu/Linux (and also macOS), needs no paid service, and remembers where it stopped, so you can run it every day until the list is finished.

## Features

- Sends the next 50 unsent addresses each run and records them in `sent.csv`
- Attaches a PDF (for example your CV)
- Random delay of about 2 minutes between emails, to look human and protect your account
- Cleans the list first: removes duplicates, invalid addresses and dead domains
- Reads Gmail bounce messages and never retries failed addresses
- Safe to stop and restart at any time

## Project structure

```
daily_mailer/
├── send_daily.py        # sends the next batch
├── clean_list.py        # cleans emails_1.csv -> emails_clean.csv
├── check_bounces.py     # records bounced addresses in bounced.csv
├── emails_1.csv         # YOUR raw list (one column named "Email")
├── subject.txt          # email subject (one line)
├── body.txt             # email body (plain text)
└── CV.pdf               # attachment (name set in send_daily.py)
```

Files created automatically: `emails_clean.csv`, `emails_rejected.csv`, `sent.csv`, `bounced.csv`, `log.txt`.

## Requirements

- Python 3.9 or newer
- A Gmail account with **2-Step Verification** turned on
- A Gmail **App Password** (explained below)
- One extra Python package: `dnspython` (only for `clean_list.py`)

## Setup

### 1. Get the files

Put all the files in one folder, for example `~/daily_mailer`, then open a terminal in it:

```bash
cd ~/daily_mailer
```

### 2. Create a virtual environment and install the dependency

Recent Ubuntu versions block `pip install` outside a virtual environment, so use one.

With **uv**:
```bash
uv venv
uv pip install --python .venv/bin/python dnspython
```

Or with plain Python:
```bash
python3 -m venv .venv
.venv/bin/pip install dnspython
```

Check it works:
```bash
.venv/bin/python -c "import dns.resolver; print('dnspython OK')"
```

### 3. Create a Gmail App Password

Your normal Gmail password will not work.

1. Go to <https://myaccount.google.com/security> and enable **2-Step Verification**.
2. Go to <https://myaccount.google.com/apppasswords>.
3. Create an app password (any name, for example "mailer").
4. Copy the 16-character password.

### 4. Prepare your list

Create `emails_1.csv` with a header line named `Email`, then one address per line:

```
Email
contact@company-one.com
hr@company-two.ma
```

The header line is required. Without it, the first address is treated as the header and skipped.

### 5. Write your message

- `subject.txt`: the subject, on one line.
- `body.txt`: the message in plain text. Keep an unsubscribe sentence at the end, for example: *"If you do not wish to receive further messages, simply reply 'unsubscribe'."*

### 6. Add your attachment

Copy your PDF into the folder. If its name is not `CV_Mouaad_Essaghir.pdf`, open `send_daily.py` and change this line:

```python
ATTACHMENT = BASE / "CV_Mouaad_Essaghir.pdf"
```

If the file does not exist, the script sends the email without an attachment.

### 7. Clean the list

```bash
.venv/bin/python clean_list.py
```

This takes a few minutes. It creates:

- `emails_clean.csv`: the addresses that will be used
- `emails_rejected.csv`: removed addresses with the reason (invalid syntax, duplicate, domain does not exist)

Addresses from big company domains are placed first, free webmail next, and old ISP domains (such as `menara.ma`) last, because those are more likely to be abandoned.

## Run it

### Test first (nothing is sent)

```bash
.venv/bin/python send_daily.py --dry-run
```

### Send a test to yourself

Temporarily make a copy of your clean list, put only your own address in `emails_clean.csv` (keep the `Email` header), run the script, and check your inbox and spam folder. Then restore the list and delete `sent.csv`:

```bash
cp emails_clean.csv emails_clean_backup.csv
printf 'Email\nyou@gmail.com\n' > emails_clean.csv
# ... run the script and check your inbox ...
cp emails_clean_backup.csv emails_clean.csv
rm -f sent.csv
```

### Send the real batch

```bash
export MAIL_USER="you@gmail.com"
export MAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
.venv/bin/python send_daily.py
```

With a delay of about 2 minutes between emails, 50 emails take roughly 1 hour 40 minutes. Keep the computer awake, or run it in the background:

```bash
nohup systemd-inhibit --what=sleep:idle .venv/bin/python send_daily.py > log.txt 2>&1 &
tail -f log.txt        # Ctrl+C stops watching, not the script
wc -l sent.csv         # how many emails were processed so far
```

You can stop the script at any time and run it again later. It continues with the next unsent address and never resends.

## Handle bounces

Some addresses will be invalid. Gmail sends a "Mail Delivery Subsystem" message to your inbox for each one. The script cannot see these at send time, so run this the next day, before sending again:

```bash
.venv/bin/python check_bounces.py
```

It saves failed addresses to `bounced.csv`, and `send_daily.py` skips them. If more than about 10% of a batch bounces, stop and review your list before continuing.

## Automate it daily with cron

```bash
crontab -e
```

Add one line (adjust the paths and credentials). This runs every day at 10:00 and checks bounces first:

```
0 10 * * * cd /home/YOURUSER/daily_mailer && MAIL_USER="you@gmail.com" MAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx" /home/YOURUSER/daily_mailer/.venv/bin/python check_bounces.py && /home/YOURUSER/daily_mailer/.venv/bin/python send_daily.py >> log.txt 2>&1
```

The computer must be on at that time.

## Settings you may want to change

In `send_daily.py`:

| Setting | Default | Meaning |
|---|---|---|
| `BATCH_SIZE` | `50` | Emails per run |
| `time.sleep(random.uniform(100, 140))` | 100 to 140 s | Random pause between emails |
| `ATTACHMENT` | CV file name | PDF to attach |

In `check_bounces.py`: `DAYS_BACK = 3` is how many days of bounce messages are read.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `0 emails in this batch` / `List finished.` | The CSV has no `Email` header, the file name is wrong, or the addresses are already in `sent.csv`. |
| `Run clean_list.py first` | `emails_clean.csv` does not exist yet. Run the cleaning step. |
| `Authentication failed` / `535` | Wrong App Password, or 2-Step Verification is off. Create a new App Password. |
| `externally-managed-environment` | Do not use system pip. Use the virtual environment from step 2. |
| `Install the DNS library first` | Install `dnspython` in the same environment you run the script with. |
| `SMTPServerDisconnected` | Gmail closed an idle connection during a long pause. Rerun the script. It resumes where it stopped. |
| `lookups failed: check your internet connection` | `clean_list.py` could not resolve domains. Check your connection and rerun. |
| Emails land in spam | Personalize the message, keep the volume low, and consider sending from your own domain with SPF, DKIM and DMARC configured. |

## Good practice and legal notes

- Gmail allows roughly 500 emails per day for a normal account. Stay far below that. 50 per day is a safe level.
- Send relevant, personal messages to people who have a reason to expect them. Mass unsolicited email can get your account restricted.
- Honor every unsubscribe request: remove the address from your list.
- Check the rules that apply to you for unsolicited email, such as GDPR in the EU or Law 09-08 in Morocco.
- Do not share your App Password. If you publish this project, add this to `.gitignore` so private data is not uploaded:

```
.venv/
emails_*.csv
sent.csv
bounced.csv
log.txt
*.pdf
```

## License

Use it freely for your own purposes, at your own responsibility.
