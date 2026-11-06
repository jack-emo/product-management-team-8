import os
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

STREAMLIT_URL = os.environ.get(
    "STREAMLIT_APP_URL",
    "https://team-8-pm-module.streamlit.app/",
)
WAKE_BUTTON = "//button[contains(., 'Yes, get this app back up')]"


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(STREAMLIT_URL)
        print(f"Opened {driver.current_url}")
        if "share.streamlit.io" in driver.current_url and "auth" in driver.current_url:
            print("The app sent this visit to a sign-in page. Make the app public, then run this again.")
            return 1

        wait = WebDriverWait(driver, 20)
        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, WAKE_BUTTON)))
            print("Wake button found. Clicking it.")
            button.click()
            wait.until(EC.invisibility_of_element_located((By.XPATH, WAKE_BUTTON)))
            print("Wake button clicked.")
        except TimeoutException:
            print("No wake button. The app is already awake, or the page did not finish loading.")
        return 0
    except Exception as exc:
        print(f"Could not wake the app: {exc}")
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
