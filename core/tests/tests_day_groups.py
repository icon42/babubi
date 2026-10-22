import datetime

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from django.test import TestCase
from django.utils import timezone

from core import models
from core.templatetags import days


class DayFiltersTestCase(TestCase):
    def test_short_duration(self):
        self.assertEqual(days.short_duration(None), "")
        self.assertEqual(
            days.short_duration(datetime.timedelta(minutes=50)), "50\u00a0min"
        )
        self.assertEqual(days.short_duration(datetime.timedelta(hours=2)), "2\u00a0h")
        self.assertEqual(
            days.short_duration(datetime.timedelta(hours=1, minutes=52, seconds=40)),
            "1\u00a0h\u00a052\u00a0min",
        )

    def test_duration_percent(self):
        self.assertEqual(days.duration_percent(None), 0)
        self.assertEqual(days.duration_percent(datetime.timedelta(hours=3)), 25)
        self.assertEqual(days.duration_percent(datetime.timedelta(hours=20)), 100)

    def test_day_label(self):
        today = timezone.localdate()
        self.assertEqual(days.day_label(today), "Today")
        yesterday = days.day_label(today - datetime.timedelta(days=1))
        self.assertTrue(yesterday.startswith("Yesterday · "), yesterday)
        older = today - datetime.timedelta(days=3)
        self.assertNotIn("Yesterday", days.day_label(older))
        last_year = today.replace(year=today.year - 1, day=1)
        self.assertIn(str(last_year.year)[-2:], days.day_label(last_year))

    def test_ends_next_day(self):
        start = timezone.localtime().replace(hour=21, minute=30)
        sleep = models.Sleep(start=start, end=start + datetime.timedelta(hours=9))
        self.assertTrue(days.ends_next_day(sleep))
        sleep.end = start + datetime.timedelta(hours=1)
        self.assertFalse(days.ends_next_day(sleep))


class DayGroupedListTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.child = models.Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        cls.user = get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        cls.user.settings.pagination_count = 2
        cls.user.settings.save()
        noon = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        cls.yesterday = noon - datetime.timedelta(days=1)
        cls.times = [
            noon,
            noon - datetime.timedelta(hours=2),
            noon - datetime.timedelta(hours=3),
            cls.yesterday,
        ]
        for time, solid in zip(cls.times, (False, True, False, True)):
            models.DiaperChange.objects.create(
                child=cls.child, time=time, wet=True, solid=solid
            )

    def setUp(self):
        self.c = HttpClient()
        self.c.login(username="tester", password="secret")

    def test_days_and_whole_day_summary(self):
        page = self.c.get("/changes/")
        self.assertEqual(page.status_code, 200)
        groups = page.context["days"]
        # The page holds two of today's three changes...
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["items"]), 2)
        # ...but the summary counts the whole day.
        texts = [part["text"] for part in groups[0]["summary"]]
        self.assertEqual(texts, ["3 changes", 3, 1])

    def test_previous_reaches_past_the_page(self):
        page = self.c.get("/changes/")
        items = page.context["days"][0]["items"]
        self.assertEqual(items[0].since_previous, datetime.timedelta(hours=2))
        # The page's last change is measured against the next one, on page 2.
        self.assertEqual(items[1].since_previous, datetime.timedelta(hours=1))

    def test_second_page_starts_a_new_day(self):
        page = self.c.get("/changes/?page=2")
        dates = [group["date"] for group in page.context["days"]]
        self.assertEqual(dates, [self.times[2].date(), self.yesterday.date()])

    def test_child_column_keeps_the_surname_apart(self):
        # A page whose entries all belong to one child has no child column.
        self.assertNotContains(self.c.get("/changes/"), "day-cell_child")
        other = models.Child.objects.create(
            first_name="Other", last_name="Child", birth_date=timezone.localdate()
        )
        models.DiaperChange.objects.create(
            child=other,
            time=self.times[0] - datetime.timedelta(hours=1),
            wet=True,
            solid=False,
        )
        page = self.c.get("/changes/")
        # The surname sits in its own span, which the phone layout hides.
        self.assertContains(
            page, 'title="Test Child">Test<span class="day-child-surname"> Child</span>'
        )


class SleepDiffEndTestCase(TestCase):
    def setUp(self):
        child = models.Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        self.c = HttpClient()
        self.c.login(username="tester", password="secret")
        start = timezone.localtime().replace(hour=8, minute=0, second=0, microsecond=0)
        for hours in (0, 3):
            models.Sleep.objects.create(
                child=child,
                start=start + datetime.timedelta(hours=hours),
                end=start + datetime.timedelta(hours=hours + 1),
            )

    def tearDown(self):
        models.Sleep.diff_settings.sleep_diff_end = True

    def test_from_the_end_by_default(self):
        page = self.c.get("/sleep/")
        item = page.context["days"][0]["items"][0]
        self.assertEqual(item.since_previous, datetime.timedelta(hours=2))
        self.assertContains(page, "Awake before")

    def test_from_the_start(self):
        models.Sleep.diff_settings.sleep_diff_end = False
        page = self.c.get("/sleep/")
        item = page.context["days"][0]["items"][0]
        self.assertEqual(item.since_previous, datetime.timedelta(hours=3))
        self.assertNotContains(page, "Awake before")
