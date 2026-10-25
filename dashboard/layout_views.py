# -*- coding: utf-8 -*-
import json

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from babubi.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.models import Child, Timer
from core.timer_kinds import allowed, set_kind

from . import layout, versions
from .models import DashboardLayout
from .views import ChildDashboard

ACTIVE_CHILD = "dashboard_active_child"


class ActiveChildDashboard(ChildDashboard):
    """
    A child's dashboard, which also makes that child the active one: the main
    menu names it and leads back to it (dashboard_layout.active_child).
    """

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        request.session[ACTIVE_CHILD] = self.object.slug
        return response


class DashboardLayoutEdit(PermissionRequiredMixin, View):
    """
    Applies one operation of the dashboard's edit mode to the user's layout
    and goes back to the child dashboard, still in edit mode. The page posts
    every operation by fetch and follows that redirect to the fresh page,
    swapping in what changed (dashboard_edit.js); "keys" carries a dragged
    arrangement as JSON.
    """

    permission_required = ("core.view_child",)
    http_method_names = ["post"]

    def post(self, request, slug):
        child = get_object_or_404(Child, slug=slug)
        instance = DashboardLayout.of(request.user, child)
        op = request.POST.get("op", "")
        if op == "configure":
            key = request.POST.get("key", "")
            if not layout.configure(instance, key, request.POST):
                return HttpResponseBadRequest()
        else:
            try:
                keys = json.loads(request.POST.get("keys", "null"))
            except ValueError:
                return HttpResponseBadRequest()
            if not layout.apply(
                instance,
                request.POST.get("kind", ""),
                request.POST.get("key", ""),
                op,
                keys,
            ):
                return HttpResponseBadRequest()
        instance.save()
        return HttpResponseRedirect(
            "{}?edit=1".format(reverse("core:child", args=[child.slug]))
        )


class TimerKindUpdate(LoginRequiredMixin, View):
    """
    Sets or changes what a running timer times, from its page: its owner, or
    whoever may change timers.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        timer = get_object_or_404(Timer, pk=pk)
        if timer.user_id != request.user.pk and not request.user.has_perm(
            "core.change_timer"
        ):
            raise PermissionDenied
        # A kind the user may not add counts as none, like an unknown one.
        kind = request.POST.get("kind", "")
        set_kind(timer, kind if kind in allowed(request.user) else "")
        return HttpResponseRedirect(reverse("core:timer-detail", args=[timer.pk]))


class DashboardVersion(LoginRequiredMixin, View):
    """
    The version of a child's dashboard data (dashboard/versions.py), which an
    open dashboard polls to fetch its cards only after a change.
    """

    def get(self, request, slug):
        if not request.user.has_perm("core.view_child"):
            raise PermissionDenied
        child = get_object_or_404(Child, slug=slug)
        return JsonResponse({"version": versions.version(child)})
