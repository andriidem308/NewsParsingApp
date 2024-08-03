import json

from robocorp.tasks import task
from RPA.Robocorp.WorkItems import WorkItems

from src.scrapers.latimes_scraper import LATimesScraper

library = WorkItems()


@task
def main():
    latimes_parser = LATimesScraper()
    latimes_parser.execute()

