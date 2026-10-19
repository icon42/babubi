# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy
from social_django import views as social_views

from . import branding, oidc, views

app_patterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("branding/<str:name>", branding.serve, name="branding"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "reset/",
        views.password_login_required(
            auth_views.PasswordResetView.as_view(
                success_url=reverse_lazy("babubi:password_reset_done")
            )
        ),
        name="password_reset",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.password_login_required(
            auth_views.PasswordResetConfirmView.as_view(
                success_url=reverse_lazy("babubi:password_reset_complete")
            )
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.password_login_required(auth_views.PasswordResetDoneView.as_view()),
        name="password_reset_done",
    ),
    path(
        "reset/complete/",
        views.password_login_required(auth_views.PasswordResetCompleteView.as_view()),
        name="password_reset_complete",
    ),
    path("", views.RootRouter.as_view(), name="root-router"),
    path("welcome/", views.Welcome.as_view(), name="welcome"),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/add/", views.UserAdd.as_view(), name="user-add"),
    path("users/<int:pk>/edit/", views.UserUpdate.as_view(), name="user-update"),
    path("users/<int:pk>/unlock/", views.UserUnlock.as_view(), name="user-unlock"),
    path("users/<int:pk>/delete/", views.UserDelete.as_view(), name="user-delete"),
    path("user/password/", views.UserPassword.as_view(), name="user-password"),
    path("user/settings/", views.UserSettings.as_view(), name="user-settings"),
    path("user/add-device/", views.UserAddDevice.as_view(), name="user-add-device"),
    path("settings/", include("dbsettings.urls")),
    path(
        "oidc/logout/backchannel/",
        oidc.backchannel_logout,
        name="oidc-backchannel-logout",
    ),
]

# The views of social-auth-app-django that OIDC login uses, under its
# namespace, so they stay hidden while OIDC is not a login method.
oidc_patterns = [
    path(
        "login/<str:backend>/",
        oidc.oidc_login_required(social_views.auth),
        name="begin",
    ),
    path(
        "complete/<str:backend>/",
        oidc.oidc_login_required(social_views.complete),
        name="complete",
    ),
]

urlpatterns = [
    # Other password login pages follow LOGIN_METHODS too.
    path("admin/login/", views.password_login_required(admin.site.login)),
    path(
        "api/auth/login/",
        views.password_login_required(
            auth_views.LoginView.as_view(template_name="rest_framework/login.html")
        ),
    ),
    path("admin/", admin.site.urls),
    path("oidc/", include((oidc_patterns, "social"), namespace="social")),
    path("", include("api.urls", namespace="api")),
    path("", include((app_patterns, "babubi"), namespace="babubi")),
    path("user/lang", include("django.conf.urls.i18n")),
    path("", include("core.urls", namespace="core")),
    path("", include("dashboard.urls", namespace="dashboard")),
    path("", include("reports.urls", namespace="reports")),
]

# Uploads stored on S3 are served from there. The prefix matches MEDIA_URL in
# settings; Django turns that one into an absolute URL, so it cannot be reused.
if not settings.AWS_STORAGE_BUCKET_NAME:
    urlpatterns.append(path("media/<path:path>", views.media, name="media"))
