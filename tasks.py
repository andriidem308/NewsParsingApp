from robocorp.tasks import task

from src.scrapers.latimes_scraper import LATimesScraper


@task
def main():
    latimes_parser = LATimesScraper('coronavirus', last_n_months=3, category='California')
    latimes_parser.execute()
