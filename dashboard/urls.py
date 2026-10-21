# -*- coding: utf-8 -*-
from django.urls import path

from . import layout_views, views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", views.Dashboard.as_view(), name="dashboard"),
    path(
        "children/<str:slug>/layout/",
        layout_views.DashboardLayoutEdit.as_view(),
        name="dashboard-layout",
    ),
    path(
        "children/<str:slug>/version/",
        layout_views.DashboardVersion.as_view(),
        name="dashboard-version",
    ),
    path(
        "timers/<int:pk>/kind/",
        layout_views.TimerKindUpdate.as_view(),
        name="timer-kind",
    ),
]
