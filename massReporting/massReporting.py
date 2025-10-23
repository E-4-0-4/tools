import os
import asyncio
import random
import time
from typing import Tuple, Optional
from telethon.sync import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PhoneNumberBannedError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
)
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonChildAbuse,
    InputReportReasonPornography,
    InputReportReasonCopyright,
    InputReportReasonFake,
    InputReportReasonOther,
)

# Telegram API Credentials (Get from https://my.telegram.org)
API_ID = 27157163  # Replace with your API ID
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"  # Replace with your API Hash

# Session file for persistent login
SESSION_FILE = "report_session.session"

# Official Telegram Report Categories
REPORT_REASONS = {
    "1": ("Child Abuse", InputReportReasonChildAbuse()),
    "2": ("Violence", InputReportReasonViolence()),
    "3": ("Illegal Goods", InputReportReasonOther()),
    "4": ("Illegal Adult Content", InputReportReasonPornography()),
    "5": ("Personal Data", InputReportReasonOther()),
    "6": ("Terrorism", InputReportReasonOther()),
    "7": ("Scam or Spam", InputReportReasonSpam()),
    "8": ("Copyright Violation", InputReportReasonCopyright()),
    "9": ("Fake Account", InputReportReasonFake()),
    "10": ("Other", InputReportReasonOther()),
}

BANNER = """
----------------------------------
TELEGRAM REPORT TOOL (EDUCATIONAL)
----------------------------------
This tool is for educational purposes only. Misuse violates Telegram's Terms of Service
and may result in account bans. Use responsibly.
----------------------------------
"""

async def get_user_input() -> Tuple[str, str, str, int]:
    """Prompt user for input and validate responses."""
    print(BANNER)
    
    phone = input("Enter Your Telegram Phone Number (e.g., +1234567890): ").strip()
    if not phone.startswith("+") or not phone[1:].isdigit():
        raise ValueError("Invalid phone number format. Use + followed by digits.")

    target_username = input("Enter Username or Group (e.g., @username): ").strip()
    if not target_username.startswith("@"):
        raise ValueError("Username must start with @.")

    print("\nChoose Report Reason:")
    for key, (reason_text, _) in REPORT_REASONS.items():
        print(f"   {key}. {reason_text}")
    
    reason_key = input("\nEnter Report Reason (1-10): ").strip()
    if reason_key not in REPORT_REASONS:
        raise ValueError("Invalid report reason. Choose a number between 1 and 10.")

    try:
        count = int(input("How many times to report? (1-10): ").strip())
        if count < 1 or count > 10:
            raise ValueError("Report count must be between 1 and 10.")
    except ValueError as e:
        raise ValueError("Invalid input for report count. Enter a number between 1 and 10.") from e

    return phone, target_username, reason_key, count

async def report_user(
    client: TelegramClient, target_username: str, reason_key: str, count: int
) -> None:
    """Reports a Telegram user/group/channel with the selected reason."""
    reason_text, reason_type = REPORT_REASONS[reason_key]
    print(f"\nTarget: {target_username}")
    print(f"Reporting for: {reason_text}")
    print(f"Sending {count} report(s)...\n")

    try:
        entity = await client.get_entity(target_username)
    except ValueError as e:
        print(f"Error: Could not find user or group '{target_username}' ({e}).")
        return
    except Exception as e:
        print(f"Unexpected error resolving entity: {e}")
        return

    for i in range(count):
        try:
            await client(ReportPeerRequest(
                peer=entity,
                reason=reason_type,
                message=f"Reported for {reason_text.lower()} (Educational test)"
            ))
            print(f"Report {i+1}/{count} sent successfully.")
            await asyncio.sleep(random.uniform(2, 5))  # Random delay to simulate human behavior
        except FloodWaitError as e:
            print(f"Flood Wait! Pausing for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error during report {i+1}: {e}")
            break

async def start_client(phone: str) -> Optional[TelegramClient]:
    """Initialize and authenticate Telegram client."""
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    try:
        await client.start(phone=lambda: phone)
        print("Successfully logged in.")
        return client
    except PhoneNumberBannedError:
        print("Error: This phone number is banned from Telegram.")
        return None
    except SessionPasswordNeededError:
        password = input("Enter your 2FA password: ").strip()
        try:
            await client.sign_in(password=password)
            print("Successfully logged in with 2FA.")
            return client
        except Exception as e:
            print(f"Error during 2FA authentication: {e}")
            return None
    except PhoneCodeInvalidError:
        print("Error: Invalid phone code provided.")
        return None
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        return None

async def main():
    """Main function to run the Telegram report tool."""
    try:
        phone, target_username, reason_key, count = await get_user_input()
    except ValueError as e:
        print(f"Input error: {e}")
        return

    # Clean up old session file if it exists
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
            print("Old session file removed.")
        except Exception as e:
            print(f"Error removing old session file: {e}")

    async with await start_client(phone) as client:
        if client:
            await report_user(client, target_username, reason_key, count)
        else:
            print("Failed to initialize client. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
