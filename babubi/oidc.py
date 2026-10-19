# -*- coding: utf-8 -*-
"""
OpenID Connect login on top of social-auth-app-django: the views gated by
LOGIN_METHODS, the user matching step of the pipeline and translated error
messages.
"""

from functools import wraps

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils.translation import gettext as _
from social_core.exceptions import AuthPolicyError
from social_django.middleware import SocialAuthExceptionMiddleware

from .models import access_expired


def oidc_login_required(view):
    """Hides a view while OIDC is not one of the login methods."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if "oidc" not in settings.LOGIN_METHODS:
            raise Http404
        return view(request, *args, **kwargs)

    return wrapped


def associate_by_username(backend, details, user=None, *args, **kwargs):
    """
    Pipeline step: links the OIDC account to the existing user with the same
    username. Unknown, inactive and expired users are turned away.
    """
    if user is None:
        users = get_user_model().objects.filter(
            username__iexact=details.get("username") or ""
        )
        user = users[0] if len(users) == 1 else None
    if user is None or not user.is_active or access_expired(user):
        raise AuthPolicyError(backend, stage="pipeline")
    return {"user": user}


class OIDCExceptionMiddleware(SocialAuthExceptionMiddleware):
    """Shows translated messages instead of the library's English ones."""

    def get_message(self, request, exception):
        if isinstance(exception, AuthPolicyError):
            return _("This account is not allowed to log in.")
        return _("Login with the identity provider failed. Try again later.")
