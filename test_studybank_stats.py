import unittest
from datetime import datetime, timedelta
from studybank_stats import summarize


class StatisticsTests(unittest.TestCase):
    today = datetime(2026, 10, 8).date()

    def session(self, offset, hours=1, income=100):
        day = self.today + timedelta(days=offset)
        return dict(timestamp=datetime.combine(day, datetime.min.time()).timestamp(),
                    duration=hours*3600, earnings=income, type='Session')

    def test_period_boundaries_and_zero_days(self):
        r = summarize([self.session(i) for i in [-14, -13, -7, -6, 0, 1]], 7, self.today)
        self.assertEqual(r['hours'], 2)
        self.assertEqual(r['previous_hours'], 2)
        self.assertEqual(r['daily_hours'], [1, 0, 0, 0, 0, 0, 1])
        self.assertEqual(r['previous_cumulative_earnings'][-1], 200)
        self.assertEqual(r['active_days'], 2)

    def test_multiple_sessions_and_recorded_wages(self):
        r = summarize([self.session(0, 1, 100), self.session(0, .5, 75)], 30, self.today)
        self.assertEqual(r['earnings'], 175)
        self.assertEqual(r['average_minutes'], 45)
        self.assertEqual(r['active_days'], 1)

    def test_empty_and_invalid_records(self):
        r = summarize([{}, None, self.session(0, -1), self.session(0, float('nan'))], 90, self.today)
        self.assertEqual(r['skipped'], 4)
        self.assertEqual(r['hours'], 0)
        self.assertEqual(r['average_minutes'], 0)
        self.assertEqual(len(r['dates']), 90)

    def test_all_periods_include_today(self):
        for days in (7, 30, 90):
            with self.subTest(days=days):
                r = summarize([self.session(0), self.session(1-days), self.session(-days)], days, self.today)
                self.assertEqual(r['hours'], 2)
                self.assertEqual(r['previous_hours'], 1)
                self.assertEqual(r['dates'][-1], self.today)


if __name__ == '__main__':
    unittest.main()
