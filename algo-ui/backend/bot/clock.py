from datetime import datetime, timedelta, time as dtime
from pytz import timezone

# Timezone + market hours (IST)
INDIAN_TZ = timezone("Asia/Kolkata")
MARKET_OPEN_TIME  = dtime(9, 15)
MARKET_CLOSE_TIME = dtime(15, 30)
WEEKEND_DAYS      = {5, 6}  # Saturday=5, Sunday=6

def now_india() -> datetime:
    return datetime.now(INDIAN_TZ)

def is_market_open(ts: datetime) -> bool:
    return ts.weekday() not in WEEKEND_DAYS and (MARKET_OPEN_TIME <= ts.time() < MARKET_CLOSE_TIME)

def seconds_until_market_open(ts: datetime) -> float:
    ts = ts.astimezone(INDIAN_TZ)
    today = ts.date()
    if today.weekday() not in WEEKEND_DAYS and ts.time() < MARKET_OPEN_TIME:
        next_open = INDIAN_TZ.localize(datetime.combine(today, MARKET_OPEN_TIME))
        return max(0.0, (next_open - ts).total_seconds())
    next_date = today + timedelta(days=1)
    while next_date.weekday() in WEEKEND_DAYS:
        next_date += timedelta(days=1)
    next_open = INDIAN_TZ.localize(datetime.combine(next_date, MARKET_OPEN_TIME))
    return max(0.0, (next_open - ts).total_seconds())

def seconds_to_next_bar(ts: datetime, interval_min: int) -> float:
    minute_bucket = (ts.minute // interval_min + 1) * interval_min
    hour_increment = minute_bucket // 60
    minute_bucket = minute_bucket % 60
    base = ts.replace(minute=0, second=0, microsecond=0)
    next_bar = base + timedelta(hours=hour_increment, minutes=minute_bucket)
    return max(1.0, (next_bar - ts).total_seconds())
