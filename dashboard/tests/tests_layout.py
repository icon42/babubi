# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client as HttpClient
from django.test import TestCase
from django.utils import timezone

from core.models import Child
from dashboard import layout
from dashboard.models import DashboardLayout


class ArrangementTestCase(TestCase):
    def test_new_layout_takes_the_defaults(self):
        columns, hidden, actions, hidden_actions, order = layout.arrangement(
            DashboardLayout()
        )
        self.assertEqual(columns, layout.default_columns())
        interleaved = layout.interleaved(columns)
        self.assertEqual(order, sorted(interleaved, key=interleaved.get))
        self.assertEqual(columns[0][0], "quick_actions")
        self.assertEqual(hidden, layout.default_hidden())
        self.assertIn("percentiles", hidden)
        self.assertEqual(actions, layout.default_actions())
        fixed = [key for key in actions + hidden_actions if ":" not in key]
        self.assertEqual(sorted(fixed), sorted(layout.ACTIONS_BY_KEY))

    def test_unknown_duplicate_and_missing_keys(self):
        saved = DashboardLayout(
            columns=[["gone", "sleep_last"], ["sleep_last", "statistics"]],
            hidden=["notes_recent"],
            actions=["note", "note", "gone"],
            hidden_actions=[],
        )
        columns, hidden, actions, hidden_actions, order = layout.arrangement(saved)
        self.assertEqual(len(columns), layout.COLUMNS)
        self.assertEqual(columns[0][0], "sleep_last")
        self.assertEqual(columns[1][0], "statistics")
        self.assertEqual(hidden, ["notes_recent", "percentiles"])
        keys = [key for column in columns for key in column] + hidden
        self.assertEqual(sorted(keys), sorted(layout.CARDS_BY_KEY))
        self.assertEqual(actions[0], "note")
        self.assertEqual(actions.count("note"), 1)
        self.assertNotIn("gone", actions)

    def test_interleaved(self):
        order = layout.interleaved([["a1", "a2", "a3"], ["b1"], ["c1", "c2"]])
        self.assertEqual(
            sorted(order, key=order.get), ["a1", "b1", "c1", "a2", "c2", "a3"]
        )

    def test_narrow_order(self):
        columns = [["a1", "a2", "a3"], ["b1"], ["c1", "c2"]]
        # Unknown and repeated keys go; the cards not placed yet follow, as
        # the columns interleave them.
        self.assertEqual(
            layout.narrow_order(["c2", "gone", "a1", "c2", "b1"], columns),
            ["c2", "a1", "b1", "c1", "a2", "a3"],
        )
        self.assertEqual(
            layout.narrow_order(["a3", "a1"], columns),
            ["a3", "a1", "b1", "c1", "a2", "c2"],
        )
        saved = DashboardLayout(order=["statistics", "quick_actions"])
        columns, hidden, actions, hidden_actions, order = layout.arrangement(saved)
        self.assertEqual(order[:2], ["statistics", "quick_actions"])
        self.assertEqual(sorted(order), sorted(k for c in columns for k in c))


class ApplyTestCase(TestCase):
    def setUp(self):
        self.layout = DashboardLayout()
        layout.reset(self.layout)

    def place(self, key):
        for c, column in enumerate(self.layout.columns):
            if key in column:
                return c, column.index(key)
        return None

    def test_move_within_and_across_columns(self):
        self.assertEqual(self.place("quick_actions"), (0, 0))
        self.assertTrue(layout.apply(self.layout, "card", "quick_actions", "down"))
        self.assertEqual(self.place("quick_actions"), (0, 1))
        self.assertTrue(layout.apply(self.layout, "card", "quick_actions", "right"))
        self.assertEqual(self.place("quick_actions"), (1, 1))
        self.assertTrue(layout.apply(self.layout, "card", "quick_actions", "left"))
        self.assertEqual(self.place("quick_actions"), (0, 1))
        self.assertFalse(layout.apply(self.layout, "card", "quick_actions", "left"))

    def test_hide_and_show(self):
        self.assertTrue(layout.apply(self.layout, "card", "statistics", "hide"))
        self.assertIsNone(self.place("statistics"))
        self.assertIn("statistics", self.layout.hidden)
        self.assertTrue(layout.apply(self.layout, "card", "statistics", "show"))
        self.assertEqual(
            self.place("statistics")[0], layout.DEFAULT_COLUMN["statistics"]
        )
        self.assertNotIn("statistics", self.layout.hidden)
        # Never arranged on narrow screens: the order keeps following the
        # columns, so it is not saved.
        self.assertEqual(self.layout.order, [])

    def test_order_on_narrow_screens(self):
        shown = [k for column in self.layout.columns for k in column]
        new = list(reversed(shown))
        self.assertTrue(layout.apply(self.layout, "card", "", "order", new))
        self.assertEqual(self.layout.order, new)
        # Columns untouched.
        self.assertEqual(self.layout.columns, layout.default_columns())
        # Only the shown cards, each once.
        self.assertFalse(layout.apply(self.layout, "card", "", "order", ["nope"]))
        self.assertFalse(
            layout.apply(self.layout, "card", "", "order", [shown[0], shown[0]])
        )
        self.assertFalse(layout.apply(self.layout, "card", "", "order", "statistics"))
        # A partial list (the cards one user sees) orders those among
        # themselves; the rest keep their slots.
        self.assertTrue(
            layout.apply(self.layout, "card", "", "order", [new[-1], new[0]])
        )
        self.assertEqual(self.layout.order[0], new[-1])
        self.assertEqual(self.layout.order[-1], new[0])
        self.assertEqual(self.layout.order[1:-1], new[1:-1])
        # Hiding and showing keep the arranged order current.
        self.assertTrue(layout.apply(self.layout, "card", "statistics", "hide"))
        self.assertNotIn("statistics", self.layout.order)
        self.assertTrue(layout.apply(self.layout, "card", "statistics", "show"))
        self.assertEqual(self.layout.order[-1], "statistics")
        layout.reset(self.layout)
        self.assertEqual(self.layout.order, [])


class DashboardLayoutViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.child = Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        cls.user = get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        cls.url = "/children/{}/".format(cls.child.slug)
        cls.edit_url = cls.url + "layout/"

    def setUp(self):
        self.c = HttpClient()
        self.c.login(username="tester", password="secret")

    def test_edit_mode_and_operations(self):
        page = self.c.get(self.url)
        self.assertContains(page, 'id="dashboard-quick_actions"')
        self.assertNotContains(page, 'class="dash-controls"')
        self.assertContains(page, "?child=" + self.child.slug)

        page = self.c.get(self.url + "?edit=1")
        self.assertContains(page, 'class="dash-controls"')
        response = self.c.post(
            self.edit_url, {"kind": "card", "key": "statistics", "op": "hide"}
        )
        self.assertRedirects(
            response,
            self.url + "?edit=1#dashboard-statistics",
            fetch_redirect_response=False,
        )
        saved = DashboardLayout.objects.get(user=self.user, child=self.child)
        self.assertIn("statistics", saved.hidden)
        page = self.c.get(self.url)
        self.assertNotContains(page, 'id="dashboard-statistics"')

        response = self.c.post(self.edit_url, {"op": "reset"})
        self.assertEqual(response.status_code, 302)
        saved.refresh_from_db()
        self.assertEqual(saved.hidden, layout.default_hidden())

        response = self.c.post(self.edit_url, {"kind": "card", "key": "x", "op": "up"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.c.get(self.edit_url).status_code, 405)

    def test_cards_and_actions_follow_permissions(self):
        user = get_user_model().objects.create_user(
            username="viewer", password="secret"
        )
        user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["view_child", "view_sleep", "add_sleep"]
            )
        )
        c = HttpClient()
        c.login(username="viewer", password="secret")
        page = c.get(self.url + "?edit=1")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'id="dashboard-sleep_last"')
        self.assertNotContains(page, 'id="dashboard-feeding_last"')
        dash = page.context["dash"]
        # Writing sleep, a timed kind, brings the timers along (babubi/roles.py).
        self.assertEqual([a.key for a in dash["actions"]], ["sleep", "timer"])
        self.assertEqual([a.key for a in dash["hidden_actions"]], ["timer:sleep"])

    def test_editing_needs_the_permission_to_view_children(self):
        get_user_model().objects.create_user(username="nobody", password="secret")
        c = HttpClient()
        c.login(username="nobody", password="secret")
        response = c.post(self.edit_url, {"op": "reset"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DashboardLayout.objects.filter(child=self.child).exists())


class ReportCardTestCase(TestCase):
    def setUp(self):
        self.layout = DashboardLayout()
        layout.reset(self.layout)
        self.key = layout.REPORT_PREFIX + "sleep-totals"

    def test_every_report_resolves(self):
        for report in layout.REPORTS:
            self.assertTrue(report.view().permission_required, report.key)
        self.assertIsNone(layout.card(layout.REPORT_PREFIX + "nope"))

    def test_add_hide_show_remove(self):
        self.assertTrue(layout.apply(self.layout, "card", self.key, "add"))
        self.assertEqual(self.layout.columns[0][-1], self.key)
        self.assertFalse(layout.apply(self.layout, "card", self.key, "add"))
        self.assertFalse(layout.apply(self.layout, "card", self.key, "remove"))
        self.assertTrue(layout.apply(self.layout, "card", self.key, "hide"))
        self.assertIn(self.key, self.layout.hidden)
        self.assertTrue(layout.apply(self.layout, "card", self.key, "remove"))
        self.assertNotIn(self.key, self.layout.hidden)
        keys = [key for column in self.layout.columns for key in column]
        self.assertNotIn(self.key, keys)
        # Fixed cards cannot be added or removed.
        self.assertFalse(layout.apply(self.layout, "card", "statistics", "add"))
        layout.apply(self.layout, "card", "statistics", "hide")
        self.assertFalse(layout.apply(self.layout, "card", "statistics", "remove"))

    def test_report_card_renders(self):
        child = Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        c = HttpClient()
        c.login(username="tester", password="secret")
        url = "/children/{}/".format(child.slug)
        c.post(url + "layout/", {"kind": "card", "key": self.key, "op": "add"})
        page = c.get(url)
        self.assertContains(page, 'id="dashboard-{}"'.format(self.key))
        self.assertContains(page, "/static/babubi/js/graph.")


class PercentilesTestCase(TestCase):
    def test_lms_percentiles_match_the_who_tables(self):
        from core import growth

        # Day 0 of the WHO weight-for-age table for boys: the median (M) and
        # the P97 column.
        self.assertAlmostEqual(growth.percentile("weight", "boy", 0, 3.3464), 50, 1)
        self.assertAlmostEqual(growth.percentile("weight", "boy", 0, 4.35), 97, 0)
        # Day 0 of the head circumference table for girls, P3 column.
        self.assertAlmostEqual(
            growth.percentile("head_circumference", "girl", 0, 31.651), 3, 1
        )
        self.assertIsNone(growth.percentile("height", "boy", 1857, 100))
        self.assertIsNone(growth.percentile("height", "boy", -1, 50))

    def test_configure_and_render(self):
        from core.models import Weight

        child = Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        Weight.objects.create(child=child, weight=3.3464, date=child.birth_date)
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        c = HttpClient()
        c.login(username="tester", password="secret")
        url = "/children/{}/".format(child.slug)
        self.assertNotContains(c.get(url), 'id="dashboard-percentiles"')
        c.post(url + "layout/", {"kind": "card", "key": "percentiles", "op": "show"})
        page = c.get(url)
        self.assertContains(page, 'id="dashboard-percentiles"')
        self.assertContains(page, "percentiles-settings", count=0)
        # Without the child's sex there is nothing to compare.
        self.assertNotContains(c.get(url), "percentiles-item")
        from dashboard.models import ChildProfile

        ChildProfile.objects.create(child=child, sex="boy")
        c.post(
            url + "layout/",
            {"op": "configure", "key": "percentiles", "measures": ["weight", "height"]},
        )
        saved = DashboardLayout.objects.get(user__username="tester")
        self.assertEqual(
            saved.options["percentiles"],
            {"measures": ["weight", "height"]},
        )
        page = c.get(url)
        self.assertContains(page, "50&nbsp;%")
        self.assertContains(page, "percentiles-item", count=2)


class ChildShortcutTestCase(TestCase):
    def test_other_children_are_shortcuts(self):
        first = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        second = Child.objects.create(
            first_name="Bru", last_name="X", birth_date=timezone.localdate()
        )
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        c = HttpClient()
        c.login(username="tester", password="secret")
        url = "/children/{}/".format(first.slug)
        key = layout.CHILD_PREFIX + second.slug
        dash = c.get(url + "?edit=1").context["dash"]
        self.assertIn(key, [a.key for a in dash["hidden_actions"]])
        self.assertNotIn(
            layout.CHILD_PREFIX + first.slug,
            [a.key for a in dash["hidden_actions"] + dash["actions"]],
        )
        c.post(url + "layout/", {"kind": "action", "key": key, "op": "show"})
        page = c.get(url)
        self.assertContains(page, 'href="/children/{}/"'.format(second.slug))
        self.assertIsNone(layout.action(layout.CHILD_PREFIX + "nobody"))


class PerChildLayoutTestCase(TestCase):
    def test_each_child_has_its_own_layout(self):
        first = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        second = Child.objects.create(
            first_name="Bru", last_name="X", birth_date=timezone.localdate()
        )
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        c = HttpClient()
        c.login(username="tester", password="secret")
        first_url = "/children/{}/".format(first.slug)
        second_url = "/children/{}/".format(second.slug)
        hide = {"kind": "card", "key": "statistics", "op": "hide"}
        c.post(first_url + "layout/", hide)
        self.assertNotContains(c.get(first_url), 'id="dashboard-statistics"')
        self.assertContains(c.get(second_url), 'id="dashboard-statistics"')
        self.assertEqual(DashboardLayout.objects.count(), 1)


class ChildSexTestCase(TestCase):
    def test_child_form_saves_the_sex_and_who_cards_follow_it(self):
        from core.forms import ChildForm
        from core.growth import sex_of

        child = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.assertEqual(sex_of(child), "")
        data = {
            "first_name": "Ada",
            "last_name": "X",
            "birth_date": timezone.localdate().isoformat(),
            "sex": "girl",
        }
        form = ChildForm(data, instance=child)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        child.refresh_from_db()
        self.assertEqual(sex_of(child), "girl")
        self.assertEqual(ChildForm(instance=child).fields["sex"].initial, "girl")

        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        c = HttpClient()
        c.login(username="tester", password="secret")
        reports = c.get("/children/{}/?edit=1".format(child.slug)).context["dash"][
            "reports"
        ]
        keys = [report.key for report in reports]
        self.assertIn("weight-change-girl", keys)
        self.assertNotIn("weight-change-boy", keys)


class TimerKindTestCase(TestCase):
    def setUp(self):
        from core.models import Timer

        self.child = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.owner = get_user_model().objects.create_user(
            username="owner", password="secret", is_superuser=True
        )
        self.timer = Timer.objects.create(user=self.owner, child=self.child)
        self.c = HttpClient()
        self.c.login(username="owner", password="secret")

    def test_kind_changes_and_shapes_the_page(self):
        from core.models import Timer
        from core.timer_kinds import kind_of

        url = "/timers/{}/".format(self.timer.pk)
        response = self.c.post(url + "kind/", {"kind": "sleep"})
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.assertEqual(kind_of(self.timer), "sleep")
        # With a kind, one finish button names it; without, one per kind.
        page = self.c.get(url)
        self.assertContains(page, "submit-primary btn btn-lg btn-activity", count=1)
        self.assertContains(page, "Finish and create a sleep")
        self.c.post(url + "kind/", {"kind": "nonsense"})
        self.assertEqual(kind_of(Timer.objects.get(pk=self.timer.pk)), "")
        self.assertContains(self.c.get(url), "btn-lg btn-activity activity-", count=4)

    def test_only_owner_or_change_permission(self):
        get_user_model().objects.create_user(username="other", password="secret")
        other = HttpClient()
        other.login(username="other", password="secret")
        url = "/timers/{}/kind/".format(self.timer.pk)
        response = other.post(url, {"kind": "sleep"})
        self.assertEqual(response.status_code, 403)

    def test_quick_timer_and_form_set_the_kind(self):
        from core.forms import TimerForm
        from core.models import Timer
        from core.timer_kinds import kind_of

        self.c.post("/timers/add/quick/", {"child": self.child.pk, "kind": "pumping"})
        newest = Timer.objects.order_by("-id").first()
        self.assertEqual(kind_of(newest), "pumping")
        self.c.post("/timers/add/quick/", {"child": self.child.pk, "kind": "x"})
        self.assertEqual(kind_of(Timer.objects.order_by("-id").first()), "")

        form = TimerForm(
            {"child": self.child.pk, "start": timezone.localtime(), "kind": "feeding"},
            instance=self.timer,
            user=self.owner,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(kind_of(self.timer), "feeding")

    def test_kinds_follow_the_activity_permissions(self):
        from core.forms import TimerForm
        from core.models import Timer
        from core.timer_kinds import kind_of

        # A caregiver who tracks sleep but not feedings, pumping or tummy time.
        carer = get_user_model().objects.create_user(username="carer", password="s")
        carer.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "view_child",
                    "view_timer",
                    "add_timer",
                    "change_timer",
                    "view_sleep",
                    "add_sleep",
                ]
            )
        )
        c = HttpClient()
        c.login(username="carer", password="s")

        # The quick timer menus offer sleep only.
        page = c.get("/timers/")
        self.assertContains(page, 'name="kind" value="sleep"')
        self.assertNotContains(page, 'name="kind" value="feeding"')

        # Quick timers and the kind buttons ignore a kind the user may not add.
        c.post("/timers/add/quick/", {"child": self.child.pk, "kind": "feeding"})
        timer = Timer.objects.order_by("-id").first()
        self.assertEqual(kind_of(timer), "")
        url = "/timers/{}/".format(timer.pk)
        c.post(url + "kind/", {"kind": "feeding"})
        self.assertEqual(kind_of(Timer.objects.get(pk=timer.pk)), "")
        c.post(url + "kind/", {"kind": "sleep"})
        self.assertEqual(kind_of(Timer.objects.get(pk=timer.pk)), "sleep")
        page = c.get(url)
        self.assertContains(page, 'value="sleep"')
        self.assertNotContains(page, 'value="feeding"')

        # The form offers sleep, and keeps a kind the timer already has.
        form = TimerForm(user=carer)
        self.assertEqual([k for k, _ in form.fields["kind"].choices], ["", "sleep"])
        form = TimerForm(user=carer, instance=self.timer)
        self.assertEqual([k for k, _ in form.fields["kind"].choices], ["", "sleep"])
        self.c.post("/timers/{}/kind/".format(self.timer.pk), {"kind": "feeding"})
        form = TimerForm(user=carer, instance=Timer.objects.get(pk=self.timer.pk))
        self.assertEqual(
            [k for k, _ in form.fields["kind"].choices], ["", "feeding", "sleep"]
        )

        # The quick actions of the dashboard follow too.
        self.assertTrue(layout.action_allowed(carer, layout.action("timer:sleep")))
        self.assertFalse(layout.action_allowed(carer, layout.action("timer:feeding")))

    def test_timer_kind_quick_actions(self):
        key = layout.TIMER_PREFIX + "sleep"
        url = "/children/{}/".format(self.child.slug)
        dash = self.c.get(url + "?edit=1").context["dash"]
        self.assertIn(key, [a.key for a in dash["hidden_actions"]])
        self.c.post(url + "layout/", {"kind": "action", "key": key, "op": "show"})
        page = self.c.get(url)
        self.assertContains(page, 'name="kind" value="sleep"')
        self.assertIsNone(layout.action(layout.TIMER_PREFIX + "nope"))


class DashboardVersionTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.child = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.other = Child.objects.create(
            first_name="Bru", last_name="X", birth_date=timezone.localdate()
        )
        get_user_model().objects.create_user(
            username="tester", password="secret", is_superuser=True
        )
        self.c = HttpClient()
        self.c.login(username="tester", password="secret")

    def version(self, child):
        url = "/children/{}/version/".format(child.slug)
        return self.c.get(url).json()["version"]

    def test_changes_bump_only_their_child(self):
        from core.models import DiaperChange

        before, other_before = self.version(self.child), self.version(self.other)
        change = DiaperChange.objects.create(
            child=self.child, time=timezone.now(), wet=True, solid=False
        )
        after = self.version(self.child)
        self.assertNotEqual(after, before)
        self.assertEqual(self.version(self.other), other_before)
        change.delete()
        self.assertNotEqual(self.version(self.child), after)

    def test_page_carries_the_version_and_refresh_skips_graphs(self):
        url = "/children/{}/".format(self.child.slug)
        key = layout.REPORT_PREFIX + "sleep-totals"
        self.c.post(url + "layout/", {"kind": "card", "key": key, "op": "add"})
        page = self.c.get(url)
        self.assertContains(page, 'data-version="{}"'.format(self.version(self.child)))
        self.assertContains(page, 'id="dashboard-time-words"')
        refresh = self.c.get(url + "?refresh=1").content.decode()
        self.assertIn('id="dashboard-{}"'.format(key), refresh)
        after_card = refresh.split('id="dashboard-{}"'.format(key))[1][:400]
        self.assertNotIn("card-report", after_card)
