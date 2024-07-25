from selenium.webdriver.common.by import By

from src.base_news_scraper import BaseNewsScraper
from src.modules.utils import timestamp_to_date


class LATimesScraper(BaseNewsScraper):
    scraper_name = 'latimes'

    start_url = 'https://www.latimes.com/'

    has_sorting = True
    has_pagination = True
    has_category_filter = True

    def search(self):
        self.click('//button[@data-element="search-button"]')
        self.click('//input[@data-element="search-form-input"]')
        self.fill('//input[@data-element="search-form-input"]', self.search_phrase)
        self.click('//button[@data-element="search-submit-button"]')

    def sort_results_by_date(self):
        self.click('//select[@class="select-input"]')
        self.click('//select[@class="select-input"]/option[text()="Newest"]')

    def filter_by_category(self):
        categories_elements = self.driver.find_elements('//ul[@class="search-filter-menu" and @data-name="Topics"]/li')

        for category_element in categories_elements:
            category_input = category_element.find_element(By.XPATH, './/label/input')
            category_name = category_element.find_element(By.XPATH, './/label/span')

            if category_name.text.lower() == self.category.lower():
                category_input.click()
                print(f'Filtered by category: {self.category}')
                break

    def find_articles(self):
        return self.driver.find_elements('//ul[@class="search-results-module-results-menu"]/li')

    def scrape_article_data(self, article) -> dict:
        title = article.find_element(By.XPATH, './/h3[@class="promo-title"]').text
        timestamp = article.find_element(By.XPATH, './/p[@class="promo-timestamp"]').get_attribute('data-timestamp')
        description = article.find_element(By.XPATH, './/p[@class="promo-description"]').text
        picture_src = article.find_element(By.XPATH, './/img[@class="image"]').get_attribute('src')

        return {
            'title': title,
            'date': timestamp_to_date(float(timestamp) / 1000),
            'description': description,
            'picture': picture_src,
        }

    def paginate(self):
        self.click('//div[@class="search-results-module-next-page"]/a')
