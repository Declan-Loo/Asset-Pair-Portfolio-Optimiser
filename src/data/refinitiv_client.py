import eikon as ek
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("EIKON_API_KEY")

ek.set_app_key(api_key)

@lru_cache(maxsize=None)
def get_price_timeseries(tickers, start, end, interval="daily"):
    # Allow a single string or a list/tuple of strings
    if isinstance(tickers, str):
        instruments = (tickers,)
    elif isinstance(tickers, Sequence):
        instruments = tuple(tickers)
    else:
        raise TypeError("tickers must be a string or a sequence of strings")

    df = ek.get_timeseries(
        list(instruments),
        start_date=start,
        end_date=end,
        interval=interval,
    )
    return df
