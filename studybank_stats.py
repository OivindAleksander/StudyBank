"""Read-only statistics for the existing StudyBank session schema."""
import math
from datetime import datetime, timedelta


def summarize(sessions, days=30, today=None):
    if days not in (7, 30, 90):
        raise ValueError('Period must be 7, 30 or 90 days')
    today = today or datetime.now().date()
    start = today - timedelta(days=days - 1)
    previous_start = start - timedelta(days=days)
    dates = [start + timedelta(days=i) for i in range(days)]
    hours, earnings, old_hours, old_earnings = ([0.0] * days for _ in range(4))
    selected, skipped = [], 0
    for session in sessions:
        try:
            timestamp, duration, income = (float(session[k]) for k in ('timestamp', 'duration', 'earnings'))
            if not all(math.isfinite(v) for v in (timestamp, duration, income)) or duration <= 0 or income < 0:
                raise ValueError('Invalid session')
            day = datetime.fromtimestamp(timestamp).date()
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            skipped += 1
            continue
        if start <= day <= today:
            i = (day - start).days
            hours[i] += duration / 3600
            earnings[i] += income
            selected.append(dict(timestamp=timestamp, duration=duration, earnings=income, type=str(session.get('type', 'Session'))))
        elif previous_start <= day < start:
            i = (day - previous_start).days
            old_hours[i] += duration / 3600
            old_earnings[i] += income
    cumulative, total = [], 0
    for income in old_earnings:
        total += income
        cumulative.append(total)
    return dict(dates=dates, daily_hours=hours, daily_earnings=earnings, previous_daily_hours=old_hours,
                previous_cumulative_earnings=cumulative, hours=sum(hours), earnings=sum(earnings),
                previous_hours=sum(old_hours), sessions=sorted(selected, key=lambda s: s['timestamp'], reverse=True),
                active_days=sum(h > 0 for h in hours), average_minutes=sum(hours)*60/len(selected) if selected else 0,
                skipped=skipped)
