import os
import pickle
import uuid
import pandas as pd
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

CSV_FILE = "airdrops.csv"


def load_data():
    if os.path.exists("airdrops.csv"):
        df = pd.read_csv("airdrops.csv")
    else:
        df = pd.DataFrame(columns=["title", "deadline_start", "deadline_end", "blockchain", "url", "reminder_time", "wallet_address", "delete"])
        
    if "delete" not in df.columns:
        df["delete"] = [str(uuid.uuid4()) for _ in range(len(df))]
        save_data(df)
        
    return df


def save_data(df):
    df.to_csv(CSV_FILE, index=False)


def get_credentials():
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    else:
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
           creds = Credentials.from_authorized_user_info(info=json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS']))

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return creds

def add_event_to_calendar(service, event_title, deadline, reminder_time):
    deadline_timestamp = pd.to_datetime(deadline)
    end_time = deadline_timestamp + pd.Timedelta(minutes=30)
    end_time_iso = end_time.isoformat()

    event = {
        "summary": event_title,
        "start": {"dateTime": deadline, "timeZone": "UTC"},
        "end": {"dateTime": end_time_iso, "timeZone": "UTC"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "email", "minutes": reminder_time * 60}],
        },
    }
    event = service.events().insert(calendarId="primary", body=event).execute()
    return event.get("htmlLink")


def main():
    st.title("Airdrop Task Manager")

    df = load_data()

    st.subheader("Add new Airdrop task")
    title = st.text_input("Airdrop Title")
    deadline_start = st.date_input("Deadline start")
    deadline_end = st.date_input("Deadline end")
    blockchain = st.text_input("Blockchain")
    url = st.text_input("URL")
    reminder_time = st.time_input("Reminder Time")
    reminder_time_minutes = reminder_time.hour * 60 + reminder_time.minute
    wallet_address = st.text_input("Wallet Address")
    daily = st.checkbox("Daily Reminder")

    if st.button("Add Airdrop"):
        new_airdrop = {"title": title, "deadline_start": deadline_start, "deadline_end": deadline_end, "blockchain": blockchain, "url": url, "reminder_time": reminder_time_minutes, "wallet_address": wallet_address, "delete": str(uuid.uuid4())}
        df = df.append(new_airdrop, ignore_index=True)
        save_data(df)

        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        event_title = f"{title} Airdrop Task"

        if daily:
            for i in range(30):
                event_deadline = pd.Timestamp(deadline_start) + pd.DateOffset(days=i)
                if event_deadline <= pd.Timestamp(deadline_end):
                    reminder_time_str = reminder_time.strftime("%H:%M:%S")
                    event_deadline_with_time = f"{event_deadline.date().isoformat()}T{reminder_time_str}"
                    event_link = add_event_to_calendar(service, event_title, event_deadline_with_time, reminder_time_minutes)
                    st.success(f"Event added to Google Calendar: {event_link}")
        else:
            reminder_time_str = reminder_time.strftime("%H:%M:%S")
            event_deadline_with_time = f"{deadline_start.isoformat()}T{reminder_time_str}"
            event_link = add_event_to_calendar(service, event_title, event_deadline_with_time, reminder_time_minutes)
            st.success(f"Event added to Google Calendar: {event_link}")

    st.subheader("Airdrop tasks")
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, step=1)

    # Display tasks with delete button
    for idx, row in df.iterrows():
        cols = st.columns([1, 8, 1])
        cols[1].write(f"{idx}. {row['title']} - {row['deadline_start']} - {row['deadline_end']} - {row['blockchain']} - {row['wallet_address']} - {row['url']} - {row['reminder_time']}")
        if cols[2].button("X", key=f"delete_{idx}"):
            df = df.drop(idx)
            save_data(df)
            st.experimental_rerun()

if __name__ == "__main__":
    main()
