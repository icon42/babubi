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
        self.assertEqual(order, layout.DEFAULT_ORDER)
        self.assertEqual(columns[0][0], "quick_actions")
        self.assertEqual(hidden, [])
        # Every fixed card and the default report cards, each once, the two
        # WHO weight ones (one shows, by the child's sex) side by side.
        flat = [key for column in columns for key in column]
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(sorted(flat), sorted(layout.DEFAULT_ORDER))
        for fixed in layout.CARDS:
            self.assertIn(fixed.key, flat)
        for key in ["report:sleep-pattern", "report:feeding-intervals"]:
            self.assertIn(key, flat)
        boy = flat.index("report:weight-change-boy")
        self.assertEqual(flat[boy + 1], "report:weight-change-girl")
        self.assertEqual(
            layout.DEFAULT_ORDER.index("report:weight-change-girl"),
            layout.DEFAULT_ORDER.index("report:weight-change-boy") + 1,
        )
        self.assertTrue(layout.card("report:bmi-change").removable)
        self.assertFalse(layout.card("report:sleep-pattern").removable)
        self.assertFalse(layout.card("percentiles").removable)
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
        self.assertEqual(hidden, ["notes_recent"])
        keys = [key for column in columns for key in column] + hidden
        self.assertEqual(sorted(keys), sorted(layout.DEFAULT_COLUMN))
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

    def test_columns_dragged(self):
        columns = [list(c) for c in self.layout.columns]
        moved = columns[0].pop(0)
        columns[2].append(moved)
        self.assertTrue(layout.apply(self.layout, "card", "", "columns", columns))
        self.assertEqual(self.layout.columns, columns)
        self.assertEqual(self.place(moved), (2, len(columns[2]) - 1))
        # Three lists of shown cards, each once, or nothing.
        self.assertFalse(layout.apply(self.layout, "card", "", "columns", columns[:2]))
        self.assertFalse(
            layout.apply(self.layout, "card", "", "columns", [[moved], [moved], []])
        )
        self.assertFalse(
            layout.apply(self.layout, "card", "", "columns", [["nope"], [], []])
        )
        # A card the user cannot see stays in its column, at its row.
        unseen = columns[1][1]
        partial = [[k for k in c if k != unseen] for c in columns]
        partial[0], partial[1] = partial[1], partial[0]
        self.assertTrue(layout.apply(self.layout, "card", "", "columns", partial))
        self.assertEqual(self.place(unseen), (1, 1))
        self.assertEqual(self.layout.columns[0], partial[0][:1] + partial[0][1:])

    def test_actions(self):
        self.assertTrue(layout.apply(self.layout, "action", "note", "show"))
        self.assertEqual(self.layout.actions[-1], "note")
        self.assertTrue(layout.apply(self.layout, "action", "note", "up"))
        self.assertEqual(self.layout.actions[-2], "note")
        self.assertTrue(layout.apply(self.layout, "action", "note", "hide"))
        self.assertIn("note", self.layout.hidden_actions)
        self.assertFalse(layout.apply(self.layout, "action", "note", "left"))

    def test_unknown_operations(self):
        self.assertFalse(layout.apply(self.layout, "card", "nope", "up"))
        self.assertFalse(layout.apply(self.layout, "spoon", "statistics", "up"))
        self.assertFalse(layout.apply(self.layout, "card", "statistics", "show"))


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
        # By default the sleep and feeding timers and the diaper change and
        # medication add forms, marked with a plus; a list action opens the
        # activity's list for the child.
        self.assertContains(page, 'name="kind" value="sleep"')
        self.assertContains(
            page, 'href="/changes/add/?child={}"'.format(self.child.slug)
        )
        self.assertContains(page, 'class="icon-add quick-action-badge"', count=2)
        self.assertNotContains(page, 'href="/sleep/add/?child=')
        self.c.post(self.edit_url, {"kind": "action", "key": "sleep", "op": "show"})
        page = self.c.get(self.url)
        self.assertContains(page, 'href="/sleep/?child={}"'.format(self.child.pk))
        for action in layout.ACTIONS:
            if action.url:
                self.assertTrue(action.url.endswith("-list"), action.url)
                self.assertTrue(layout.action("add:" + action.key).add)
        self.assertIsNone(layout.action("add:nope"))
        # The add form, shown, is the activity's icon with a plus.
        self.c.post(self.edit_url, {"kind": "action", "key": "add:sleep", "op": "show"})
        page = self.c.get(self.url)
        self.assertContains(page, 'href="/sleep/add/?child={}"'.format(self.child.slug))
        self.assertContains(page, 'class="icon-add quick-action-badge"', count=3)
        page = self.c.get(self.url + "?edit=1")
        self.assertContains(page, "Sleep · Add")
        # The rest wait folded away, grouped by activity: sleep, with all
        # three on the card, has no row; feeding still offers its add form
        # and list, always in that order after the timer.
        self.assertContains(page, "<summary>More actions</summary>")
        groups = {g["action"].key: g for g in page.context["available"]}
        self.assertNotIn("sleep", groups)
        self.assertEqual(
            [a.key for a in groups["feeding"]["variants"]], ["add:feeding", "feeding"]
        )
        self.c.post(self.edit_url, {"kind": "action", "key": "sleep", "op": "hide"})
        self.c.post(
            self.edit_url, {"kind": "action", "key": "timer:sleep", "op": "hide"}
        )
        page = self.c.get(self.url + "?edit=1")
        groups = {g["action"].key: g for g in page.context["available"]}
        self.assertEqual(
            [a.key for a in groups["sleep"]["variants"]], ["timer:sleep", "sleep"]
        )
        # The timer activity: start one, the add form and the timer list.
        self.assertEqual(
            [a.key for a in groups["timer"]["variants"]],
            ["timer", "add:timer", "list:timer"],
        )
        self.assertTrue(groups["timer"]["variants"][0].starts_timer)
        self.assertEqual(layout.action("add:timer").url, "core:timer-add")
        self.assertEqual(layout.action("list:timer").url, "core:timer-list")
        self.assertIsNone(layout.action("list:sleep"))
        # Every operation comes back to the edit page; the script that posts
        # them swaps in what changed (dashboard_edit.js).
        response = self.c.post(
            self.edit_url, {"kind": "action", "key": "sleep", "op": "show"}
        )
        self.assertEqual(response.url, self.url + "?edit=1")
        self.assertContains(page, 'value="add:medication"')
        # The chosen actions drag by a handle, each row named by its key.
        self.assertContains(
            page, 'class="quick-actions-edit quick-actions-edit_sortable'
        )
        self.assertContains(page, '<li data-key="add:diaperchange">')

        page = self.c.get(self.url + "?edit=1")
        self.assertContains(page, 'class="dash-controls"')
        self.assertContains(page, 'data-layout-url="' + self.edit_url + '"')
        self.assertContains(page, "Babubi.DashboardEdit.init")
        self.assertContains(page, 'class="dash-handle d-lg-none"')
        self.assertContains(page, 'data-move="up"')
        self.assertNotContains(page, 'value="left"')
        # The toggle unfolds the cards with settings: quick actions and
        # percentiles.
        self.assertEqual(
            page.content.decode().count('class="btn btn-sm dash-btn dash-toggle'), 2
        )
        self.assertContains(page, 'id="dashboard-quick_actions"')
        quick = page.content.decode().split('id="dashboard-quick_actions"')[1]
        self.assertIn("dash-toggle", quick.split("</form>")[0])

        response = self.c.post(
            self.edit_url, {"kind": "card", "key": "statistics", "op": "hide"}
        )
        self.assertRedirects(
            response, self.url + "?edit=1", fetch_redirect_response=False
        )
        saved = DashboardLayout.objects.get(user=self.user, child=self.child)
        self.assertIn("statistics", saved.hidden)
        page = self.c.get(self.url)
        self.assertNotContains(page, 'id="dashboard-statistics"')

        response = self.c.post(self.edit_url, {"kind": "card", "key": "x", "op": "up"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.c.get(self.edit_url).status_code, 405)

    def test_dragged_arrangements_are_saved(self):
        import json

        def drag(op, keys, kind="card"):
            return self.c.post(
                self.edit_url, {"kind": kind, "op": op, "keys": json.dumps(keys)}
            )

        columns = layout.default_columns()
        shown = [key for column in columns for key in column]
        response = drag("order", list(reversed(shown)))
        self.assertRedirects(
            response, self.url + "?edit=1", fetch_redirect_response=False
        )
        saved = DashboardLayout.objects.get(user=self.user, child=self.child)
        self.assertEqual(saved.order, list(reversed(shown)))
        # The page positions the cards by it: of the reversed default, the
        # first card this child shows (the WHO cards need a sex) is first.
        page = self.c.get(self.url)
        self.assertRegex(
            page.content.decode(),
            r'id="dashboard-statistics"\s+style="--dash-order: 0"',
        )
        self.assertNotContains(page, "data-column=")

        columns[0], columns[2] = columns[2], columns[0]
        response = drag("columns", columns)
        self.assertEqual(response.status_code, 302)
        saved.refresh_from_db()
        self.assertEqual(saved.columns, columns)
        self.assertEqual(saved.order, list(reversed(shown)))

        # The quick actions dragged into an order, among the chosen ones.
        actions = layout.default_actions()
        self.assertEqual(drag("order", actions[::-1], kind="action").status_code, 302)
        saved.refresh_from_db()
        self.assertEqual(saved.actions, actions[::-1])
        self.assertEqual(drag("order", ["add:sleep"], kind="action").status_code, 400)

        self.assertEqual(drag("order", ["nope"]).status_code, 400)
        self.assertEqual(drag("columns", [[], []]).status_code, 400)
        response = self.c.post(
            self.edit_url, {"kind": "card", "op": "order", "keys": "{not json"}
        )
        self.assertEqual(response.status_code, 400)

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
        # Writing sleep, a timed kind, brings the timers along (babubi/roles.py):
        # of the default actions, the sleep timer.
        self.assertEqual([a.key for a in dash["actions"]], ["timer:sleep"])
        self.assertEqual(
            [a.key for a in dash["hidden_actions"]],
            ["sleep", "timer", "add:sleep", "add:timer", "list:timer"],
        )
        # Reading alone opens the lists, not the add forms nor a timer.
        user.user_permissions.remove(Permission.objects.get(codename="add_sleep"))
        dash = c.get(self.url + "?edit=1").context["dash"]
        self.assertEqual([a.key for a in dash["actions"]], [])
        self.assertEqual(
            [a.key for a in dash["hidden_actions"]], ["sleep", "list:timer"]
        )

    def test_editing_needs_the_permission_to_view_children(self):
        get_user_model().objects.create_user(username="nobody", password="secret")
        c = HttpClient()
        c.login(username="nobody", password="secret")
        response = c.post(
            self.edit_url, {"kind": "card", "key": "statistics", "op": "hide"}
        )
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
        # The girl's WHO weight card is on the page by default, the others
        # of her sex wait in the picker; no boy's one anywhere.
        self.assertIn("height-change-girl", keys)
        self.assertNotIn("weight-change-girl", keys)
        self.assertNotIn("height-change-boy", keys)
        page = c.get("/children/{}/".format(child.slug))
        self.assertContains(page, 'id="dashboard-report:weight-change-girl"')
        self.assertNotContains(page, 'id="dashboard-report:weight-change-boy"')


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
        key = layout.TIMER_PREFIX + "pumping"
        url = "/children/{}/".format(self.child.slug)
        dash = self.c.get(url + "?edit=1").context["dash"]
        self.assertIn(key, [a.key for a in dash["hidden_actions"]])
        self.c.post(url + "layout/", {"kind": "action", "key": key, "op": "show"})
        page = self.c.get(url)
        self.assertContains(page, 'name="kind" value="pumping"')
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
