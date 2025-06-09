from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        _LOGGER.debug("Starting parse_data method")
        driver = None
        WAIT_TIME = 10  # seconds

        try:
            page = "https://selfservice.broxtowe.gov.uk/renderform.aspx?t=217&k=9D2EF214E144EE796430597FB475C3892C43C528"
            _LOGGER.debug(f"Using URL: {page}")

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            _LOGGER.debug(f"Input parameters - UPRN: {user_uprn}, Postcode: {user_postcode}, WebDriver: {web_driver}, Headless: {headless}")

            check_uprn(user_uprn)
            check_postcode(user_postcode)
            _LOGGER.debug("Input validation passed")

            # Create Selenium webdriver
            _LOGGER.debug("Creating webdriver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)
            _LOGGER.debug("Page loaded")

            # Wait for form to be loaded
            _LOGGER.debug("Waiting for form to load")
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located((By.ID, "selfservice-page"))
            )
            _LOGGER.debug("Form loaded successfully")

            # Populate postcode field
            _LOGGER.debug("Entering postcode")
            inputElement_postcode = WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located(
                    (By.ID, "ctl00_ContentPlaceHolder1_FF5683TB")
                )
            )
            inputElement_postcode.send_keys(user_postcode)
            _LOGGER.debug(f"Postcode entered: {user_postcode}")

            # Click search button
            _LOGGER.debug("Clicking search button")
            search_button = WebDriverWait(driver, WAIT_TIME).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_ContentPlaceHolder1_FF5683BTN")
                )
            )
            search_button.click()
            _LOGGER.debug("Search button clicked")

            # Wait for the 'Select address' dropdown to appear and select option matching UPRN
            _LOGGER.debug("Waiting for address dropdown")
            dropdown = WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located(
                    (By.ID, "ctl00_ContentPlaceHolder1_FF5683DDL")
                )
            )
            # Create a 'Select' for it, then select the matching URPN option
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value("U" + user_uprn)
            _LOGGER.debug(f"Address selected with UPRN: {user_uprn}")

            # Wait for the submit button to appear, then click it to get the collection dates
            _LOGGER.debug("Waiting for submit button")
            submit = WebDriverWait(driver, WAIT_TIME).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_ContentPlaceHolder1_btnSubmit")
                )
            )
            submit.click()
            _LOGGER.debug("Submit button clicked")

            # Wait for the results to load
            _LOGGER.debug("Waiting for results to load")
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located(
                    (By.ID, "ctl00_ContentPlaceHolder1_FF5686FormGroup")
                )
            )
            _LOGGER.debug("Results loaded")

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            _LOGGER.debug("Page source parsed with BeautifulSoup")

            bins_div = soup.find("div", id="ctl00_ContentPlaceHolder1_FF5686FormGroup")
            if not bins_div:
                _LOGGER.debug("No bins div found")
                return data

            bins_table = bins_div.find("table")
            if not bins_table:
                _LOGGER.debug("No bins table found")
                return data

            COLUMN_BIN_TYPE = 0
            COLUMN_NEXT_COLLECTION = 3

            # Get table rows, skip the header row
            _LOGGER.debug("Processing bin collection data")
            for row in bins_table.find_all("tr")[1:]:
                try:
                    # Get the rows cells
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        _LOGGER.debug("Row has insufficient cells, skipping")
                        continue

                    # Example: GREEN 240L
                    bin_type = cells[COLUMN_BIN_TYPE].get_text(strip=True)
                    if not bin_type:
                        _LOGGER.debug("No bin type found, skipping")
                        continue

                    next_collection = cells[COLUMN_NEXT_COLLECTION].get_text(strip=True)
                    if not next_collection:
                        _LOGGER.debug("No next collection date found, skipping")
                        continue

                    # Format: Wednesday, 02 July 2025
                    collection_date = datetime.strptime(
                        cells[COLUMN_NEXT_COLLECTION].get_text(strip=True), "%A, %d %B %Y"
                    )
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)
                    _LOGGER.debug(f"Added bin collection: {dict_data}")
                except Exception as e:
                    _LOGGER.debug(f"Error processing row: {e}")
                    continue

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
            )
            _LOGGER.debug(f"Final bin collection data: {data}")

        except Exception as e:
            _LOGGER.debug(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                _LOGGER.debug("Closing webdriver")
                driver.quit()

        return data
