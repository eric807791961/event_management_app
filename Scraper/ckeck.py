import csv
import logging
import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Maximize window and set to fullscreen
    driver.maximize_window()
    driver.fullscreen_window()
    
    return driver

def ensure_maximized(driver):
    # Get the initial window size
    initial_size = driver.get_window_size()
    
    # Attempt to maximize again
    driver.maximize_window()
    driver.fullscreen_window()
    
    # Wait for the window size to stabilize
    WebDriverWait(driver, 10).until(
        lambda d: d.get_window_size() != initial_size
    )

def scrape_event_data(driver, link):
    try:
        driver.get(link)
        ensure_maximized(driver)
        event_data = {'link': link}

        # Extract event name and image URL
        try:
            event_name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="banner"]/div[2]/h1'))
            ).text
            event_data['event_name'] = event_name

            image_url = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="banner"]/div[1]/img'))
            ).get_attribute('src')
            event_data['image_url'] = image_url
        except TimeoutException:
            logging.warning(f"Timeout while extracting event data for link: {link}")
            return None, None

        # Extract session data
        sessions = []
        try:
            session_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="buyTicket"]/div[2]/div/div[1]'))
            )
            
            # Get all text elements within the found element
            text_elements = session_element.find_elements(By.XPATH, './/*[text()]')
            texts = [elem.text.strip() for elem in text_elements if elem.text.strip()]
            
            # Process texts into sessions, assuming 4 fields per session
            for i in range(0, len(texts) - 3, 4):
                session_data = {
                    'event_link': link,
                    'session_name': texts[i],
                    'session_date': texts[i+1],
                    'session_time': texts[i+2],
                    'session_location': texts[i+3]
                }
                sessions.append(session_data)
        except TimeoutException:
            logging.warning(f"No sessions found for link: {link}")
        except Exception as e:
            logging.error(f"Error extracting session data for link {link}: {str(e)}", exc_info=True)

        return event_data, sessions
    except WebDriverException:
        logging.error(f"WebDriver error for link {link}. Skipping.", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error occurred for link {link}: {str(e)}", exc_info=True)
    return None, None

def insert_data_to_postgres(conn, events, sessions):
    try:
        cursor = conn.cursor()

        for event in events:
            cursor.execute("""
                INSERT INTO events (link, event_name, image_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (link) DO UPDATE
                SET event_name = EXCLUDED.event_name,
                    image_url = EXCLUDED.image_url
                RETURNING id
            """, (event['link'], event['event_name'], event['image_url']))
            event_id = cursor.fetchone()[0]

            event_sessions = [s for s in sessions if s['event_link'] == event['link']]
            for session in event_sessions:
                cursor.execute("""
                    INSERT INTO sessions (event_id, session_name, session_date, session_time, session_location)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, session_name, session_date, session_time) 
                    DO UPDATE SET
                        session_location = EXCLUDED.session_location
                """, (event_id, session['session_name'], session['session_date'], session['session_time'], session['session_location']))

        conn.commit()
        logging.info(f"Successfully inserted {len(events)} events and {len(sessions)} sessions into the database.")

    except (Exception, psycopg2.Error) as error:
        logging.error("Error while inserting data:", exc_info=True)
        conn.rollback()

def main():
    db_params = {
        "dbname": "event_management",
        "user": "event_user",
        "password": "Eric8077818!",
        "host": "localhost",
        "port": "5432"
    }

    driver = initialize_driver()
    events = []
    all_sessions = []

    try:
        conn = psycopg2.connect(**db_params)
        
        with open('event_links.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header if it exists
            next(reader)  # Skip the first link
            links = [row[0] for row in reader]

        for link in links:
            event_data, sessions = scrape_event_data(driver, link)
            if event_data:
                events.append(event_data)
                all_sessions.extend(sessions)

        insert_data_to_postgres(conn, events, all_sessions)

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
    finally:
        driver.quit()
        if conn:
            conn.close()
            logging.info("PostgreSQL connection is closed")

if __name__ == "__main__":
    main()