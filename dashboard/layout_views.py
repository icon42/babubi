# -*- coding: utf-8 -*-
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from babubi.mixins import LoginRequiredMixin
from core.models import Child

from . import layout
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


class DashboardLayoutEdit(LoginRequiredMixin, View):
    """
    Applies one operation of the dashboard's edit mode to the user's layout
    and goes back to the child dashboard, still in edit mode.
    """

    http_method_names = ["post"]

    def post(self, request, slug):
        child = get_object_or_404(Child, slug=slug)
        instance = DashboardLayout.of(request.user, child)
        op = request.POST.get("op", "")
        if op == "reset":
            layout.reset(instance)
        elif op == "configure":
            key = request.POST.get("key", "")
            if not layout.configure(instance, key, request.POST):
                return HttpResponseBadRequest()
        elif not layout.apply(
            instance, request.POST.get("kind", ""), request.POST.get("key", ""), op
        ):
            return HttpResponseBadRequest()
        instance.save()
        url = reverse("core:child", args=[child.slug])
        anchor = request.POST.get("key", "")
        return HttpResponseRedirect(
            "{}?edit=1{}".format(url, "#dashboard-" + anchor if anchor else "")
        )
