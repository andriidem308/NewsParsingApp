import datetime
import logging
import os.path
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from urllib.request import urlretrieve

from RPA.Browser.Selenium import Selenium
from RPA.Excel.Files import Files
from RPA.Robocorp.WorkItems import WorkItems
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.modules import utils


OUTPUT_DIR = 'output/'
PICTURES_DIR = os.path.join(OUTPUT_DIR, 'pictures')

EXCEL_HEADERS = ["title", "date", "description", "picture", "phrases_amount", "contains_money"]


class BaseNewsScraper(ABC):

    has_pagination = False
    has_category_filter = False

    viewport_x = 1400
    viewport_y = 1000

    page_load_timeout = 5

    def __init__(self) -> None:
        self.work_items = WorkItems()
        self.work_items.get_input_work_item()
        work_items_input_data = self.work_items.get_work_item_variables()

        search_phrase = work_items_input_data.get('search_phrase', '')
        last_n_months = work_items_input_data.get('last_n_months', 0)
        category = work_items_input_data.get('category')

        self.search_phrase = search_phrase
        self.category = category
        self.oldest_date = utils.get_oldest_date(last_n_months)

        self.driver = Selenium()

        self.articles = []

        self.logger = logging.getLogger(__name__)

    def execute(self) -> None:
        self.create_dirs_if_not_exist()

        self.driver.open_available_browser()
        self.driver.set_window_size(self.viewport_x, self.viewport_y)

        self.driver.go_to(self.start_url)
        print(f'Start page {self.start_url} opened')

        print(f'Start searching articles via search input')
        self.search()

        print(f'Sorting results (Newest first)')
        self.sort_results_by_date()
        print(f'Results sorted!')

        if self.category is not None and self.has_category_filter:
            print(f'Filtering results by category "{self.category}"')
            self.filter_by_category()
            print(f'Results filtered!')

        print(f'Collecting articles')
        self.parse_page()
        print(f'Articles collected!')

        print(f'Trying to save results to the excel file')
        self.save_articles()

    def create_dirs_if_not_exist(self) -> None:
        if not os.path.exists(OUTPUT_DIR):
            print(f'{OUTPUT_DIR} does not exist. Creating output directory...')
            os.mkdir(OUTPUT_DIR)
            print(f'Output directory created')

        if not os.path.exists(PICTURES_DIR):
            print(f'{PICTURES_DIR} does not exist. Creating pictures directory...')
            os.mkdir(PICTURES_DIR)
            print(f'Pictures directory created')

    @utils.method_delay
    @abstractmethod
    def search(self) -> None:
        raise NotImplementedError('Scraper must implement method search()')

    @utils.method_delay
    @abstractmethod
    def sort_results_by_date(self) -> None:
        raise NotImplementedError('Scraper must implement method sort_results_by_date()')

    @utils.method_delay
    def filter_by_category(self) -> None:
        raise NotImplementedError(
            'Scraper must implement method filter_by_category() if category filter is available and category provided')

    def parse_page(self) -> None:
        utils.delay()

        article_elements = self.find_articles()

        for article_element in article_elements:
            article_data = self.scrape_article_data(article_element)
            if article_data['date'] < self.oldest_date:
                return

            processed_article_data = self.process_article_data(article_data)

            self.articles.append(processed_article_data)

        if self.has_pagination:
            self.paginate()
            self.parse_page()

    def wait_for_element_clickable(self, selector, selector_type='xpath'):
        element = WebDriverWait(self.driver.driver, 10).until(
                EC.element_to_be_clickable((self.get_selector_type(selector_type), selector)))
        return element

    @staticmethod
    def get_selector_type(selector_type):
        match selector_type:
            case 'xpath':
                result = By.XPATH
            case 'css':
                result = By.CSS_SELECTOR
            case 'class_name':
                result = By.CLASS_NAME
            case 'id':
                result = By.ID
            case _:
                raise ValueError(f'Invalid selector type: {selector_type}')
        return result

    @abstractmethod
    def find_articles(self) -> List[WebElement]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def scrape_article_data(article: WebElement) -> Dict[str, Any]:
        raise NotImplementedError

    def process_article_data(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(article_data['date'], datetime.date):
            article_data['date'] = article_data['date'].isoformat()
        article_data['phrases_amount'] = utils.get_phrases_amount(self.search_phrase, article_data)
        article_data['contains_money'] = utils.check_money_noted(article_data)
        self.download_picture(article_data)
        return article_data

    def download_picture(self, article_data: Dict[str, Any]) -> None:
        picture_url = article_data['picture']

        picture_filename = f"{article_data['title'].lower().replace(' ', '_')}.{picture_url.split('.')[-1]}"

        picture_filepath = os.path.join(PICTURES_DIR, picture_filename)

        try:
            urlretrieve(picture_url, picture_filepath)
            print(f'Picture {picture_filename} downloaded successfully')
            article_data['picture'] = picture_filename
        except ValueError:
            print(f"Picture can't be downloaded via URI {picture_url}")

    @utils.method_delay
    @abstractmethod
    def paginate(self) -> None:
        pass

    @property
    @abstractmethod
    def start_url(self) -> str:
        pass

    @property
    @abstractmethod
    def scraper_name(self) -> str:
        pass

    def click(self, xpath: str) -> None:
        element = self.wait_for_element_clickable(xpath)
        element.click()

    @utils.method_delay
    def fill(self, xpath: str, text: str) -> None:
        self.driver.input_text(xpath, text)

    def save_articles(self) -> None:
        self.work_items.create_output_work_item({'articles': self.articles}, save=True)

        lib = Files()
        lib.create_workbook(path=f"output/{self.scraper_name}.xlsx", fmt="xlsx")

        lib.append_rows_to_worksheet([EXCEL_HEADERS], start=1)
        for article_data in self.articles:
            lib.append_rows_to_worksheet(article_data)
        lib.auto_size_columns("A", "F", width=16)
        lib.save_workbook()
