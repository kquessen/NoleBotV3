import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
import json
import string
import random
import time
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from datetime import datetime

# ======== Load environment variables ========
load_dotenv()
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# ======== Google Sheets Setup ========
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('../json/nolebot-credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open('NoleBot Verification').sheet1

# ======== Verification Code Utilities ========
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def load_verified():
    try:
        with open('../json/verified.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_verified(data):
    with open('../json/verified.json', 'w') as f:
        json.dump(data, f, indent=2)

def load_last_timestamp():
    try:
        with open('../json/poll_state.json') as f:
            data = json.load(f)
            return data.get("last_timestamp")
    except FileNotFoundError:
        return None

def save_last_timestamp(timestamp_str):
    with open('../json/poll_state.json', 'w') as f:
        json.dump({"last_timestamp": timestamp_str}, f, indent=2)

# ======== Send Email ========
def send_verification_email(to_email, code):
    msg = EmailMessage()
    msg['Subject'] = 'Your FSU Discord Verification Code from NoleBot'
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = to_email
    msg['Reply-To'] = GMAIL_ADDRESS

    msg.set_content(
        f"""
Hi there,

This is an automatic message from NoleBot, the official FSU Esports Discord verification system.

Your verification code is: {code}

To complete verification, please DM this code to the NoleBot Discord bot using the /verify command.

If you did not request this code or submitted the form in error, you can safely ignore this email.

Thank you,
FSU NoleBot Team
"""
    )

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

# ======== Polling Loop ========
def poll_sheet():
    while True:
        print("🔁 Checking for new submissions...")
        verified = load_verified()
        records = sheet.get_all_records()

        last_timestamp_raw = load_last_timestamp()
        last_timestamp = datetime.strptime(last_timestamp_raw, '%m/%d/%Y %H:%M:%S') if last_timestamp_raw else None
        max_timestamp_seen = last_timestamp

        for entry in records:
            timestamp_str = entry.get("Timestamp")
            email = entry.get("FSU Student Email")
            discord_tag = entry.get("Discord Tag")

            if not timestamp_str or not email or not discord_tag:
                continue

            try:
                timestamp_dt = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
            except ValueError:
                print(f"⚠️ Skipping invalid timestamp format: {timestamp_str}")
                continue

            if last_timestamp and timestamp_dt <= last_timestamp:
                continue

            # Generate and send code
            code = generate_code()
            try:
                send_verification_email(email, code)
                verified[email] = {
                    "code": code,
                    "timestamp": time.time(),
                    "discord_tag": discord_tag,
                    "dm_sent": False
                }
                print(f"✅ Sent code to {email} ({discord_tag})")

                # Track newest timestamp seen
                if not max_timestamp_seen or timestamp_dt > max_timestamp_seen:
                    max_timestamp_seen = timestamp_dt

            except Exception as e:
                print(f"❌ Failed to send email for {email} ({discord_tag}): {e}")

        save_verified(verified)
        if max_timestamp_seen:
            save_last_timestamp(max_timestamp_seen.strftime('%m/%d/%Y %H:%M:%S'))

        time.sleep(60)

if __name__ == '__main__':
    poll_sheet()
