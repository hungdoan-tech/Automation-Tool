import os
import time
import threading
import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from Automated_Task import AutomatedTask
from Utilities import get_excel_data_in_column_start_at_row, extract_zip, \
    check_parent_folder_contain_all_required_sub_folders, join_set_of_elements
from Logger import centralized_logger


class AutomatedTicketCottonOn(AutomatedTask):
    __ticket_cotton_on_file_download_extension: str = '.zip'

    def __init__(self, settings: dict[str, str]):
        super().__init__(settings)

    def automate(self) -> None:
        centralized_logger.info("-------------------------------------------------------------------------------------------------------------")
        centralized_logger.info("Start processing")

        self._driver.get('https://app.shipeezi.com/')

        centralized_logger.info('Try to login')
        self.__login()
        centralized_logger.info("Login successfully")

        centralized_logger.info("Navigate to overview Booking page the first time")
        # click navigating operations on header
        self._click_when_element_present(by=By.CSS_SELECTOR, value='div[data-cy=nav-Operations]')
        # click navigating overview bookings page - on the header
        self._click_and_wait_navigate_to_other_page(by=By.CSS_SELECTOR, value='li[data-cy=bookings]')

        booking_ids: set[str] = get_excel_data_in_column_start_at_row(self._settings['excel.path'],
                                                                      self._settings['excel.sheet'],
                                                                      self._settings['excel.read_column.start_cell'])
        if len(booking_ids) == 0:
            centralized_logger.error('Input booking id list is empty ! Please check again')

        last_booking: str = ''
        for booking in booking_ids:
            centralized_logger.info("Processing booking : " + booking)
            self.__navigate_and_download(booking)
            last_booking = booking

        self._driver.close()
        centralized_logger.info("-------------------------------------------------------------------------------------------------------------")
        centralized_logger.info("End processing")
        centralized_logger.info("Summary info about list of successful and unsuccessful attempts to download each "
                                "booking's documents during the program")

        # Display summary info to the user
        self.__check_up_all_downloads(booking_ids, last_booking)

        # Pause and wait for the user to press Enter
        centralized_logger.info("It ends at {}. Press any key to end program...".format(datetime.datetime.now()))
        input()

    def __login(self) -> None:
        username: str = self._settings['username']
        password: str = self._settings['password']

        self._type_when_element_present(by=By.ID, value='user-mail', content=username)
        self._type_when_element_present(by=By.ID, value='pwd', content=password)
        self._click_and_wait_navigate_to_other_page(by=By.CSS_SELECTOR, value='button[type=submit]')

    def __check_up_all_downloads(self, booking_ids: set[str], last_booking: str) -> None:
        last_booking_downloaded_folder: str = os.path.join(self._downloadFolder, last_booking)
        self._wait_download_file_complete(last_booking_downloaded_folder)

        is_all_contained, successful_bookings, unsuccessful_bookings = check_parent_folder_contain_all_required_sub_folders(
            parent_folder=self._downloadFolder, required_sub_folders=booking_ids)

        centralized_logger.info('{} successful booking folders containing documents has been download'
                                .format(len(successful_bookings)))
        successful_bookings = join_set_of_elements(successful_bookings, " ")
        centralized_logger.info(successful_bookings)

        if not is_all_contained:
            centralized_logger.error('{} fail attempts for downloading documents in all these bookings'
                                     .format(len(unsuccessful_bookings)))
            successful_bookings = join_set_of_elements(unsuccessful_bookings, " ")
            centralized_logger.info(successful_bookings)

    def __navigate_and_download(self, booking: str) -> None:
        search_box: WebElement = self._type_when_element_present(by=By.CSS_SELECTOR,
                                                                 value='div[data-cy=search] input',
                                                                 content=booking)

        # try to click option_booking - which usually out of focus and be removed from the DOM / cause exception
        try_attempt_count: int = 0
        while True:
            try:
                if try_attempt_count > 20:
                    raise Exception('Look like we have problems with the web structure changed - '
                                    'we could not click on the option_booking ! Need to our investigation')

                time.sleep(1 * self._timingFactor)
                self._driver.find_element(by=By.CSS_SELECTOR, value='.MuiAutocomplete-option:nth-child(1)').click()
                centralized_logger.info('Clicked option_booking for {} successfully'.format(booking))
                break
            except Exception as exception:
                centralized_logger.error(exception.args[0] if exception.args else None)

                time.sleep(1 * self._timingFactor)
                self._driver.execute_script("arguments[0].value = '{}';".format(booking), search_box)

                time.sleep(1 * self._timingFactor)
                search_box.click()

                centralized_logger.info('The {}th sent new key and click to try revoke the autocomplete board show up '
                                        'option_booking for {}'.format(try_attempt_count , booking))
                try_attempt_count += 1
                continue

        # click detail booking
        self._click_when_element_present(by=By.CSS_SELECTOR, value='td[data-cy=table-cell-actions] '
                                                                   'div[data-cy=action-details]'
                                                                   ':nth-child(2)')
        # click tab document
        self._click_when_element_present(by=By.CSS_SELECTOR, value='button[data-cy=documents]')

        # click view file
        self._click_when_element_present(by=By.CSS_SELECTOR, value='div[data-cy=shipment-documents-box] '
                                                                   '.MuiGrid-container '
                                                                   '.MuiGrid-item:nth-child(6) button')

        # wait until the progress bar on view file disappear
        time.sleep(1 * self._timingFactor)
        WebDriverWait(self._driver, 120 * self._timingFactor).until(ec.invisibility_of_element(
            (By.CSS_SELECTOR, 'div[data-cy=shipment-documents-box] .MuiGrid-container '
                              '.MuiGrid-item:nth-child(6) button .progressbar')))

        self._wait_to_close_all_new_tabs_except_the_current()

        # click downLoad all files
        self._click_when_element_present(by=By.CSS_SELECTOR, value='div[data-cy=shipment-documents-box] '
                                                                   'div:nth-child(2) button')

        full_file_path: str = os.path.join(self._downloadFolder, booking +
                                           self.__ticket_cotton_on_file_download_extension)
        self._wait_download_file_complete(full_file_path)
        extract_zip_task = threading.Thread(target=extract_zip, args=(full_file_path, self._downloadFolder, 1, True))
        extract_zip_task.daemon = True
        extract_zip_task.start()

        # click to back to the overview Booking page
        self._click_and_wait_navigate_to_other_page(by=By.CSS_SELECTOR,
                                                    value='.MuiBreadcrumbs-ol .MuiBreadcrumbs-li:nth-child(1)')
        centralized_logger.info("Navigating back to overview Booking page")
