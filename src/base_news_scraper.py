import logging
import os.path
from abc import ABC, abstractmethod
from urllib.request import urlretrieve

from RPA.Browser.Selenium import Selenium
from RPA.Excel.Files import Files

from src.modules import utils

LOGGER = logging.getLogger('rpa_scraper_logger')

OUTPUT_DIR = '../output'
PICTURES_DIR = os.path.join(OUTPUT_DIR, 'pictures')

EXCEL_HEADERS = ["title", "date", "description", "picture", "phrases_amount", "contains_money"]


class BaseNewsScraper(ABC):
    browser_options = {
        'use_profile': False,
        'headless': 'AUTO',
        'maximized': False,
        'browser_selection': 'AUTO',
        'alias': None,
        'profile_name': None,
        'profile_path': None,
        'preferences': None,
        'proxy': None,
        'user_agent': None,
        'download': 'AUTO',
        'options': None,
        'port': None,
        'sandbox': False,
    }

    has_pagination = False
    has_category_filter = False

    viewport_x = 1400
    viewport_y = 1000

    page_load_timeout = 5

    def __init__(self, search_phrase: str, last_n_months: int = 0, category: str = None) -> None:
        self.search_phrase = search_phrase
        self.driver = Selenium()
        self.category = category

        self.oldest_date = utils.get_oldest_date(last_n_months)

        self.articles = []

    def execute(self) -> None:
        self.create_dirs_if_not_exist()

        self.driver.open_available_browser(**self.browser_options)
        self.driver.set_window_size(self.viewport_x, self.viewport_y)

        self.driver.go_to(self.start_url)
        LOGGER.info(f'Start page {self.start_url} opened')

        LOGGER.info(f'Start searching articles via search input')
        self.search()

        LOGGER.info(f'Sorting results (Newest first)')
        self.sort_results_by_date()

        if self.category is not None and self.has_category_filter:
            LOGGER.info(f'Filtering results by category "{self.category}"')
            self.filter_by_category()

        LOGGER.info(f'Collecting articles')
        self.parse_page()
        LOGGER.info(f'Articles collected!')

        LOGGER.info(f'Trying to save results to the excel file')
        self.save_articles_to_excel()

    @staticmethod
    def create_dirs_if_not_exist():
        if not os.path.exists(OUTPUT_DIR):
            LOGGER.info(f'{OUTPUT_DIR} does not exist. Creating output directory...')
            os.mkdir(OUTPUT_DIR)
            LOGGER.info(f'Output directory created')

        if not os.path.exists(PICTURES_DIR):
            LOGGER.info(f'{PICTURES_DIR} does not exist. Creating pictures directory...')
            os.mkdir(PICTURES_DIR)
            LOGGER.info(f'Pictures directory created')

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

    def parse_page(self):
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

    @abstractmethod
    def find_articles(self) -> list:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def scrape_article_data(article):
        raise NotImplementedError

    def process_article_data(self, article_data):
        article_data['phrases_amount'] = utils.get_phrases_amount(self.search_phrase, article_data)
        article_data['contains_money'] = utils.check_money_noted(article_data)
        self.download_picture(article_data)

        return article_data

    @staticmethod
    def download_picture(article_data):
        picture_url = article_data['picture']

        picture_filename = f"{article_data['title'].lower().replace(' ', '_')}.{picture_url.split('.')[-1]}"

        picture_filepath = os.path.join(PICTURES_DIR, picture_filename)

        try:
            urlretrieve(picture_url, picture_filepath)
            LOGGER.info(f'Picture {picture_filename} downloaded successfully')
            article_data['picture'] = picture_filename
        except ValueError:
            LOGGER.info(f"Picture can't be downloaded via URI {picture_url}")

    @utils.method_delay
    @abstractmethod
    def paginate(self):
        pass

    @property
    @abstractmethod
    def start_url(self):
        pass

    @property
    @abstractmethod
    def scraper_name(self):
        pass

    @utils.method_delay
    def click(self, xpath):
        self.driver.click_element(xpath)

    @utils.method_delay
    def fill(self, xpath, text):
        self.driver.input_text(xpath, text)

    def save_articles_to_excel(self):
        lib = Files()
        lib.create_workbook(path=f"../output/{self.scraper_name}.xlsx", fmt="xlsx")

        articles_data = [[article[key] for key in EXCEL_HEADERS] for article in self.articles]
        lib.append_rows_to_worksheet([EXCEL_HEADERS] + articles_data, header=True)

        lib.save_workbook()
