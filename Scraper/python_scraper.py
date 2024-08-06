from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd
import psycopg2
from psycopg2 import sql
import csv

def get_element_link(driver, element):
    try:
        return driver.execute_script("""
            var elm = arguments[0];
            var event = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            
            // Store the current URL
            var currentUrl = window.location.href;
            
            // Add event listener to prevent navigation
            var preventNavigation = function(e) { e.preventDefault(); };
            window.addEventListener('beforeunload', preventNavigation);
            
            // Dispatch the event
            elm.dispatchEvent(event);
            
            // Capture the URL that would have been navigated to
            var newUrl = window.location.href;
            
            // Remove the event listener
            window.removeEventListener('beforeunload', preventNavigation);
            
            // Restore the original URL if it changed
            if (window.location.href !== currentUrl) {
                window.history.pushState({}, '', currentUrl);
            }
            
            return newUrl;
        """, element)
    except Exception as e:
        print(f"Error using JavaScript to extract URL: {str(e)}")
        return None

def scroll_and_load_elements(driver):
    # Scroll down to the button and click it to enable scrolling
    try:
        wait = WebDriverWait(driver, 10)
        button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '查看更多活動')]")))
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        time.sleep(2)  # Wait for the scroll to complete
        button.click()
        print("Clicked the button to enable scrolling.")
    except TimeoutException:
        print("'查看更多活動' button not found or not clickable.")
        return

    # Scroll to the bottom of the page
    while True:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load

        # Check if we've reached the end of the page
        try:
            end_of_page = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '已經沒有更多活動囉！')]"))
            )
            print("Reached end of page. Stopping scroll.")
            break
        except TimeoutException:
            print("More content available. Continuing to scroll.")

    # Find all event elements
    base_xpath = '//*[@id="app"]/div/div/div/main/div/div/div[2]/div[2]/div/div/div[1]'
    return driver.find_elements(By.XPATH, f"{base_xpath}/div")

def find_event_links(driver):
    url = "https://ticketplus.com.tw/"
    links = []
    last_successful_index = 0
    base_xpath = '//*[@id="app"]/div/div/div/main/div/div/div[2]/div[2]/div/div/div[1]/div'

    try:
        driver.get(url)

        def scroll_and_load_elements(driver):
            # Scroll down to the button and click it to enable scrolling
            try:
                wait = WebDriverWait(driver, 10)
                button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '查看更多活動')]")))
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(2)  # Wait for the scroll to complete
                button.click()
                print("Clicked the button to enable scrolling.")
            except TimeoutException:
                print("'查看更多活動' button not found or not clickable.")
                return

            # Scroll to the bottom of the page
            while True:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load

                # Check if we've reached the end of the page
                try:
                    end_of_page = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '已經沒有更多活動囉！')]"))
                    )
                    print("Reached end of page. Stopping scroll.")
                    break
                except TimeoutException:
                    print("More content available. Continuing to scroll.")

            # Find all event elements
            base_xpath = '//*[@id="app"]/div/div/div/main/div/div/div[2]/div[2]/div/div/div[1]'
            return driver.find_elements(By.XPATH, f"{base_xpath}/div")

        elements = scroll_and_load_elements(driver)
        print(f"Found {len(elements)} elements to process.")

        ignored_exceptions = (NoSuchElementException, StaleElementReferenceException)

        while last_successful_index < len(elements):
            try:
                for i in range(last_successful_index, len(elements)):
                    element = WebDriverWait(driver, 10, ignored_exceptions=ignored_exceptions).until(
                        EC.presence_of_element_located((By.XPATH, f"{base_xpath}[{i+1}]/div"))
                    )

                    link = get_element_link(driver, element)

                    if link and link not in links:
                        print(f"Element {i+1}: Found new link - {link}")
                        links.append(link)
                    else:
                        print(f"Element {i+1}: No link found or duplicate link.")

                    last_successful_index = i + 1

            except Exception as e:
                print(f"Error processing element {last_successful_index + 1}: {str(e)}")
                driver.get(url)
                elements = scroll_and_load_elements(driver)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

    print(f"\nTotal unique links found: {len(links)}")
    
    # Save links to CSV
    with open('event_links.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Link'])  # Header
        for link in links:
            writer.writerow([link])
    
    print("Links saved to event_links.csv")
    return links

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")  # Uncomment for headless mode

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    driver.fullscreen_window()
    return driver

def scrape_event_data(links, driver):
    events = []
    sessions = []
    xpaths = {
        'event_name': '//*[@id="banner"]/div[2]/h1',
        'image_url': '//*[@id="banner"]/div[1]/img',
        'sessions_container': '//*[@id="buyTicket"]/div[2]'
    }

    for i, link in enumerate(links, 1):
        try:
            driver.get(link)
            print(f"Processing link {i}/{len(links)}: {link}")

            event_data = {'link': link}
            
            # Wait for event name and extract it
            try:
                event_name_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpaths['event_name']))
                )
                event_data['event_name'] = event_name_element.text
            except TimeoutException:
                print(f"Event name not found for link: {link}")
                event_data['event_name'] = None

            # Wait for image and extract its URL
            try:
                image_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpaths['image_url']))
                )
                event_data['image_url'] = image_element.get_attribute('src')
            except TimeoutException:
                print(f"Image not found for link: {link}")
                event_data['image_url'] = None

            # Extract session data
            try:
                sessions_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpaths['sessions_container']))
                )
                session_texts = sessions_container.find_elements(By.XPATH, './/*[text()]')
                session_data = {
                    'event_link': link,
                    'session_info': [text.text for text in session_texts if text.text.strip()]
                }
                sessions.append(session_data)
            except TimeoutException:
                print(f"No sessions found for link: {link}")

            events.append(event_data)

        except WebDriverException:
            print(f"WebDriver error for link {link}. Recreating driver.")
            driver.quit()
            driver = initialize_driver()
            continue  # Skip to the next link
        except Exception as e:
            print(f"Error processing link {link}: {str(e)}")

    return pd.DataFrame(events), pd.DataFrame(sessions), driver

def insert_data_to_postgres(events_df, sessions_df):
    # PostgreSQL connection parameters
    db_params = {
        "dbname": "event_management",
        "user": "event_user",
        "password": "Eric8077818!",
        "host": "localhost",
        "port": "5432"
    }

    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Insert events data
        for _, event in events_df.iterrows():
            cursor.execute("""
                INSERT INTO events (link, event_name, image_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (link) DO UPDATE
                SET event_name = EXCLUDED.event_name,
                    image_url = EXCLUDED.image_url
                RETURNING id
            """, (event['link'], event['event_name'], event['image_url']))
            event_id = cursor.fetchone()[0]

            # Insert sessions data
            event_sessions = sessions_df[sessions_df['event_link'] == event['link']]
            for _, session in event_sessions.iterrows():
                cursor.execute("""
                    INSERT INTO sessions (event_id, session_name, session_date, session_time, session_location)
                    VALUES (%s, %s, %s, %s, %s)
                """, (event_id, session['session_name'], session['session_date'], session['session_time'], session['session_location']))

        conn.commit()
        print(f"Successfully inserted {len(events_df)} events and {len(sessions_df)} sessions into the database.")

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL or inserting data:", error)

    finally:
        if conn:
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")

def main():
    driver = initialize_driver()

    try:
        links = find_event_links(driver)
        print(f"Found {len(links)} links.")

        events_df, sessions_df, driver = scrape_event_data(links, driver)

        print("\nEvent Data:")
        print(events_df.head())
        print("\nSession Data:")
        print(sessions_df.head())

        # Save to CSV
        events_df.to_csv('event_data.csv', index=False, encoding='utf-8-sig')
        sessions_df.to_csv('session_data.csv', index=False, encoding='utf-8-sig')
        print("\nData saved to CSV files")

        # Insert data into PostgreSQL
        insert_data_to_postgres(events_df, sessions_df)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()