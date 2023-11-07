import os
import time
import logging

from abc import abstractmethod
from typing import Callable
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import AnyDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions

from Download_Driver import place_suitable_chromedriver, get_full_browser_driver_path
from Logger import centralized_logger


class AutomatedTask:

    def __init__(self, settings: dict[str, str]):
        self._settings: dict[str, str] = settings

        self._downloadFolder = self._settings['download.path']
        if not os.path.isdir(self._downloadFolder):
            centralized_logger.info(f"Provided download folder '{self._downloadFolder}'is not valid. It is a file, "
                                    f"not folder")
            raise Exception(f"Provided download folder '{self._downloadFolder}'is not valid. It is a file, "
                                    f"not folder")

        if not os.path.exists(self._downloadFolder):
            os.makedirs(self._downloadFolder)
            centralized_logger.info(f"Create folder '{self._downloadFolder}' because it is not existed by default")

        if self._settings['time.unit.factor'] is None:
            self._timingFactor = 1.0
        else:
            self._timingFactor = float(self._settings['time.unit.factor'])

        if self._settings['time.unit.factor'] is not None:
            self._use_gui = 'True'.lower() == str(self._settings['use.GUI']).lower()

        if not self._use_gui:
            centralized_logger.info('Run in headless mode')

        browser_driver: str = get_full_browser_driver_path()
        self._driver = self._setup_driver(browser_driver)

    @abstractmethod
    def automate(self):
        pass

    def _setup_driver(self,
                      browser_driver: str) -> WebDriver:

        options: webdriver.ChromeOptions = webdriver.ChromeOptions()

        if not self._use_gui:
            options.add_argument("--headless")
            options.add_argument('--disable-gpu')
            options.add_argument("--window-size=%s" % "1920,1080")
            options.add_argument("--use-fake-ui-for-media-stream")
        else:
            options.add_argument("--start-maximized")

        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')

        download_path: str = self._downloadFolder
        prefs: dict = {
            "profile.default_content_settings.popups": 0,
            "download.default_directory": r'{}'.format(download_path),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "excludeSwitches": ['enable-logging']
        }
        if not self._use_gui:
            prefs['plugins.always_open_pdf_externally'] = True

        options.add_experimental_option("prefs", prefs)

        if not os.path.exists(browser_driver):
            place_suitable_chromedriver()
        service: webdriver.ChromeService = webdriver.ChromeService(executable_path=r'{}'.format(browser_driver))

        driver: webdriver.Chrome = webdriver.Chrome(service=service, options=options)
        return driver

    def _wait_download_file_complete(self, file_path: str) -> None:
        centralized_logger.info(r'Waiting for downloading {} complete'.format(file_path))
        attempt_counting: int = 0
        max_attempt: int = 60 * 3
        while True:
            if attempt_counting > max_attempt:
                raise Exception('The webapp waiting too long to download {}. Please check'.format(file_path))

            if not os.path.exists(file_path):
                time.sleep(1 * self._timingFactor)
                attempt_counting += 1
                continue

            break
        centralized_logger.info(r'Downloading {} complete'.format(file_path))

    def _wait_navigating_to_other_page_complete(self, previous_url) -> None:
        attempt_counting: int = 0
        max_attempt: int = 30
        while True:
            current_url: str = self._driver.current_url

            if attempt_counting > max_attempt:
                raise Exception('The webapp is not navigating as expected, previous url is{}'.format(previous_url))

            if current_url == previous_url:
                time.sleep(1 * self._timingFactor)
                attempt_counting += 1
                continue

            break

    def _wait_to_close_all_new_tabs_except_the_current(self):
        current_attempt: int = 0
        max_attempt: int = 60 * 3
        while True:
            number_of_current_tabs: int = len(self._driver.window_handles)
            if current_attempt > max_attempt:
                logging.error('Can not load the file')
                raise Exception('Can not load the file')

            if number_of_current_tabs > 1:
                time.sleep(1 * self._timingFactor)
                runner: int = number_of_current_tabs
                while runner > 1:
                    time.sleep(1 * self._timingFactor)
                    self._driver.switch_to.window(self._driver.window_handles[runner - 1])
                    self._driver.close()
                    runner = runner - 1

                self._driver.switch_to.window(self._driver.window_handles[0])
                break
            else:
                time.sleep(1 * self._timingFactor)
                current_attempt = current_attempt + 1

    def _type_when_element_present(self, by: str, value: str, content: str, time_sleep: int = 1) -> WebElement:
        web_element: WebElement = self.__get_element_satisfy_predicate(by,
                                                                       value,
                                                                       expected_conditions.presence_of_element_located(
                                                                           (by, value)),
                                                                       time_sleep)

        web_element.send_keys(content)
        return web_element

    def _click_when_element_present(self, by: str, value: str, time_sleep: int = 1) -> WebElement:
        web_element: WebElement = self.__get_element_satisfy_predicate(by,
                                                                       value,
                                                                       expected_conditions.presence_of_element_located(
                                                                           (by, value)),
                                                                       time_sleep)

        web_element.click()
        return web_element

    def _click_and_wait_navigate_to_other_page(self, by: str, value: str, time_sleep: int = 1) -> WebElement:
        previous_url: str = self._driver.current_url
        web_element: WebElement = self.__get_element_satisfy_predicate(by,
                                                                       value,
                                                                       expected_conditions.presence_of_element_located(
                                                                           (by, value)),
                                                                       time_sleep)
        web_element.click()
        self._wait_navigating_to_other_page_complete(previous_url=previous_url)
        return web_element

    def __get_element_satisfy_predicate(self,
                                        by: str,
                                        element_selector: str,
                                        method: Callable[[AnyDriver], WebElement],
                                        time_sleep: int = 1) -> WebElement:
        time.sleep(time_sleep * self._timingFactor)
        if self._use_gui:
            WebDriverWait(self._driver, 10 * self._timingFactor).until(method)
        queried_element: WebElement = self._driver.find_element(by=by, value=element_selector)
        return queried_element
