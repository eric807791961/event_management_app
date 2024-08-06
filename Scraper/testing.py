import csv
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.maximize_window()
    return driver

def check_element_and_get_texts(driver, link):
    try:
        driver.get(link)
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="buyTicket"]/div[2]/div/div[1]'))
        )
        logging.info(f"Element found for link: {link}")
        
        # Get all text elements within the found element
        text_elements = element.find_elements(By.XPATH, './/*[text()]')
        texts = [elem.text.strip() for elem in text_elements if elem.text.strip()]
        
        return True, texts
    except (TimeoutException, NoSuchElementException):
        logging.warning(f"Element not found for link: {link}")
        return False, []
    except Exception as e:
        logging.error(f"Error checking link {link}: {str(e)}")
        return False, []

def main():
    driver = initialize_driver()
    try:
        with open('event_links.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header if it exists
            next(reader)  # Skip the first link
            links = [row[0] for row in reader]

        results = []
        for link in links:
            element_found, texts = check_element_and_get_texts(driver, link)
            results.append((link, element_found, texts))

        print("\nResults:")
        for link, element_found, texts in results:
            print(f"Link: {link}")
            print(f"Element found: {'Yes' if element_found else 'No'}")
            if element_found:
                print("Texts found:")
                for text in texts:
                    print(f"  - {text}")
            print("---")

        success_count = sum(1 for _, found, _ in results if found)
        print(f"\nSummary: Element found in {success_count} out of {len(results)} links.")

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()