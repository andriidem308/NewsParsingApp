from src.scrapers.latimes_scraper import LATimesScraper

if __name__ == '__main__':
    latimes_parser = LATimesScraper('coronavirus', last_n_months=3, category='California')
    latimes_parser.execute()

