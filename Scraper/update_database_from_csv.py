import pandas as pd
import psycopg2
from psycopg2 import sql

def update_database_from_csv(events_csv, sessions_csv):
    # PostgreSQL connection parameters
    db_params = {
        "dbname": "event_management",
        "user": "event_user",
        "password": "Eric8077818!",
        "host": "localhost",
        "port": "5432"
    }

    # Read CSV files
    events_df = pd.read_csv(events_csv, encoding='utf-8-sig')
    sessions_df = pd.read_csv(sessions_csv, encoding='utf-8-sig')

    print("Event CSV columns:", events_df.columns.tolist())
    print("Session CSV columns:", sessions_df.columns.tolist())

    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Update events table
        for _, event in events_df.iterrows():
            if pd.isna(event['event_name']) or pd.isna(event['image_url']):
                print(f"Skipping event with missing data: {event['link']}")
                continue

            cursor.execute("""
                INSERT INTO events (link, event_name, image_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (link) DO UPDATE
                SET event_name = EXCLUDED.event_name,
                    image_url = EXCLUDED.image_url
                RETURNING id
            """, (event['link'], event['event_name'], event['image_url']))
            event_id = cursor.fetchone()[0]

            # Update sessions table
            event_sessions = sessions_df[sessions_df['event_link'] == event['link']]
            for _, session in event_sessions.iterrows():
                if pd.isna(session['session_name']) or pd.isna(session['session_date']) or pd.isna(session['session_time']) or pd.isna(session['session_location']):
                    print(f"Skipping session with missing data for event: {event['link']}")
                    continue

                cursor.execute("""
                    INSERT INTO sessions (event_id, session_name, session_date, session_time, session_location)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, session_name, session_date, session_time)
                    DO UPDATE
                    SET session_location = EXCLUDED.session_location
                """, (event_id, session['session_name'], session['session_date'], session['session_time'], session['session_location']))

        conn.commit()
        print(f"Successfully processed {len(events_df)} events and {len(sessions_df)} sessions in the database.")

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL or updating data:", error)
        if 'event' in locals():
            print("Problematic event row:", event)
        if 'session' in locals():
            print("Problematic session row:", session)

    finally:
        if conn:
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")

if __name__ == "__main__":
    events_csv = 'event_data.csv'
    sessions_csv = 'session_data.csv'
    update_database_from_csv(events_csv, sessions_csv)