from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import time
import os
import sys

CHROME_NODE_URL = os.getenv("CHROME_NODE_URL")
BASE_URL = os.getenv("BASE_URL")

class InsiderTests:
    """Insider website test automation suite for k8s."""
    
    def __init__(self):
        """Initialize WebDriver connection."""
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # connection retry logic
        for attempt in range(5):
            try:
                self.driver = webdriver.Remote(
                    command_executor=CHROME_NODE_URL,
                    options=options
                )
                self.driver.set_window_size(1920, 1080)
                self.wait = WebDriverWait(self.driver, 15)
                print(f"Connected to Chrome Node: {CHROME_NODE_URL}")
                break
            except Exception as e:
                if attempt < 4:
                    print("Connection failed, retrying...")
                    time.sleep(5)
                else:
                    print(f"Connection failed: {e}")
                    raise
        
    def test_homepage(self):
        """Verify homepage loads and URL is correct."""
        try:
            self.driver.get(BASE_URL)
        except (TimeoutException, WebDriverException) as e:
            print(f"Homepage failed to load: {e}")
            return False
            
        current_url = self.driver.current_url
        if "useinsider.com" in current_url:
            print(f"Correct page: {current_url}")
            return True
        else:
            print(f"Wrong page: {current_url}")
            return False
        
    def test_careers_navigation(self):
        """Navigate to Careers page and verify required sections exist."""
        try:
            company_menu = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Company')]")))
            company_menu.click()
            time.sleep(0.5)
            
            careers_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Careers')]")))
            careers_link.click()
        except TimeoutException:
            print("Navigation elements not found")
            return False
            
        current_url = self.driver.current_url
        if "careers" not in current_url.lower():
            print(f"Not on careers page: {current_url}")
            return False
        
        # verify blocks exist
        time.sleep(1)
        try:            
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Find your calling')]")))
            time.sleep(0.5)
            self.driver.find_element(By.XPATH, "//*[contains(text(), 'Our Locations')]")
            time.sleep(0.5)
            self.driver.find_element(By.XPATH, "//*[contains(text(), 'Life at Insider')]")
        except (TimeoutException, NoSuchElementException):
            print("Careers page blocks not found")
            return False
            
        print("Careers page blocks verified")
        return True
        
    def page_cookies(self):
        """Reject cookie consent popup if present."""
        try:
            cookie_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "wt-cli-reject-btn"))
            )
            cookie_button.click()
            print("Cookie consent rejected")
            time.sleep(1)
        except (TimeoutException, NoSuchElementException):
            print("Cookie consent not found")
        except Exception as e:
            print(f"Cookie handling error: {e}")
    
    def test_qa_jobs_filter(self):
        """Filter QA jobs by Istanbul location and Quality Assurance department."""
        try:
            self.driver.get(f"{BASE_URL}/careers/quality-assurance/")
        except (TimeoutException, WebDriverException):
            print("QA page failed to load")
            return False
            
        try:
            see_all_jobs = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'See all QA jobs')]")))
            see_all_jobs.click()
            time.sleep(5)
            
            self.page_cookies()
            
            while True:
                try:
                    location_filter = self.wait.until(EC.element_to_be_clickable((By.ID, "select2-filter-by-location-container")))
                    location_filter.click()
                    time.sleep(0.5)
                    istanbul_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Istanbul, Turkiye')]")))
                    istanbul_option.click()
                    break
                except TimeoutException:
                    print("Refreshing page")
                    self.driver.refresh()
                    time.sleep(5)
            
            # Filter by department
            department_filter = self.wait.until(EC.element_to_be_clickable((By.ID, "select2-filter-by-department-container")))
            department_filter.click()
            time.sleep(0.5)
            qa_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Quality Assurance')]")))
            qa_option.click()
            time.sleep(2)
        except TimeoutException:
            print("Filter elements not found")
            return False
            
        jobs = self.driver.find_elements(By.CLASS_NAME, "position-list-item")
        if jobs:
            print(f"QA jobs filtered successfully: {len(jobs)} jobs found")
            return True
        else:
            print("No QA jobs found after filtering")
            return False
        
    def test_job_details(self):
        """Verify job listings match filter criteria."""
        jobs = self.driver.find_elements(By.CLASS_NAME, "position-list-item")
        if not jobs:
            print("No jobs found for verification")
            return False
        
        try:
            for job in jobs[:3]:
                position = job.find_element(By.CLASS_NAME, "position-title").text
                department = job.find_element(By.CLASS_NAME, "position-department").text
                location = job.find_element(By.CLASS_NAME, "position-location").text
                
                if "Quality Assurance" not in position:
                    print(f"Invalid position: {position}")
                    return False
                if "Quality Assurance" not in department:
                    print(f"Invalid department: {department}")
                    return False
                if "Istanbul, Turkiye" not in location:
                    print(f"Invalid location: {location}")
                    return False
        except NoSuchElementException:
            print("Job detail elements not found")
            return False
        
        print("Job details verified")
        return True
            
    def test_lever_redirect(self):
        """Verify 'View Role' redirects to Lever application page."""
        try:
            job_card = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "position-list-item")))
            view_role_button = job_card.find_element(By.XPATH, ".//a[contains(@class, 'btn') or contains(text(), 'View Role')]")
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", view_role_button)
            time.sleep(0.5)

            self.driver.execute_script("arguments[0].click();", view_role_button)
            time.sleep(2)
        except (TimeoutException, NoSuchElementException) as e:
            print(f"View Role button not found: {e}")
            return False
            
        # Lever Application form page
        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[1])
        
        current_url = self.driver.current_url
        if "jobs.lever.co" in current_url.lower():
            time.sleep(1)
            qa_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Quality Assurance')]")
            if qa_elements:
                print(f"Lever redirect successful: {current_url}")
                return True
            
            print("Quality Assurance text not found on Lever page")
            return False
        
        print(f"Lever redirect failed: {current_url}")
        return False
        
    def run_all(self):
        """Execute all tests and print results summary."""
        results = []
        try:
            results.append(("Homepage", self.test_homepage()))
            results.append(("Careers Navigation", self.test_careers_navigation()))
            results.append(("QA Jobs Filter", self.test_qa_jobs_filter()))
            results.append(("Job Details", self.test_job_details()))
            results.append(("Lever Redirect", self.test_lever_redirect()))
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            print(f"\nTest Results: {passed}/{total} passed")
            for test_name, result in results:
                status = "PASS" if result else "FAIL"
                print(f"  {test_name}: {status}")
            
            # keep container alive
            print("\nTests completed.")
            while True:
                time.sleep(3600)
                
        finally:
            self.driver.quit()


if __name__ == "__main__":
    tests = InsiderTests()
    tests.run_all()
