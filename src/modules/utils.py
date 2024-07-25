import datetime
import re
import time
from typing import Dict, Any, Callable


def method_delay(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        time.sleep(2)
        func(*args, **kwargs)
        time.sleep(2)

    return wrapper


def delay(seconds: [int, float] = 3) -> None:
    time.sleep(seconds)


def get_phrases_amount(search_phrase: str, article: Dict[str, Any]) -> int:
    title_count = article['title'].lower().count(search_phrase.lower())
    description_count = article['description'].lower().count(search_phrase.lower())
    return description_count + title_count


def timestamp_to_date(timestamp: float) -> datetime.date:
    return datetime.datetime.fromtimestamp(timestamp).date()


def check_money_noted(article: Dict[str, Any]) -> bool:
    money_regex = r'\$[\d,]+(\.\d+)?|\d+\s(dollars|USD)'
    money_noted_in_title = bool(re.search(money_regex, article['title']))
    money_noted_in_description = bool(re.search(money_regex, article['description']))
    return money_noted_in_title or money_noted_in_description


def get_oldest_date(last_n_months: int = 0) -> datetime.date:
    # Realization could be different due to requirements, I provide simple variant

    if last_n_months < 0:
        raise ValueError("Last n months must be non-negative")
    elif last_n_months == 0:
        last_n_months = 1

    oldest_date = (datetime.datetime.now() - datetime.timedelta(days=30 * last_n_months - 1)).date()
    return oldest_date
