# -*- coding: utf-8 -*-
"""
OpenID Connect login on top of social-auth-app-django: the views gated by
LOGIN_METHODS, the user matching step of the pipeline, translated error
messages and back-channel logout.
"""

from functools import wraps

import jwt
from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from social_core.exceptions import (
    AuthAssociationError,
    AuthPolicyError,
    SocialAuthBaseException,
)
from social_django import views as social_views
from social_django.middleware import SocialAuthExceptionMiddleware
from social_django.models import UserSocialAuth
from social_django.utils import load_backend, load_strategy

from .models import access_expired

BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"


def oidc_login_required(view):
    """Hides a view while OIDC is not one of the login methods."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if "oidc" not in settings.LOGIN_METHODS:
            raise Http404
        return view(request, *args, **kwargs)

    return wrapped


def associate_existing_user(backend, details, response, user=None, *args, **kwargs):
    """
    Pipeline step: the first time a provider account logs in, finds the one
    existing user it belongs to, by the verified email or by the username
    (OIDC_MATCH_BY); a user who is already logged in links to it directly.
    Unknown, inactive and expired users are turned away.
    """
    if user is None:
        user = matching_user(backend, details, response)
    if user is None or not user.is_active or access_expired(user):
        raise AuthPolicyError(backend, stage="pipeline")
    return {"user": user}


def matching_user(backend, details, response):
    """
    The existing user the provider's claims name, or None: exactly one match,
    without case, and in email mode only an email the provider has verified.
    """
    if settings.OIDC_MATCH_BY == "username":
        lookup = {"username__iexact": details.get("username") or ""}
    else:
        if not details.get("email") or not email_verified(backend, response):
            return None
        lookup = {"email__iexact": details["email"]}
    if not any(lookup.values()):
        return None
    users = list(get_user_model().objects.filter(**lookup)[:2])
    return users[0] if len(users) == 1 else None


def email_verified(backend, response):
    """The email_verified claim, from the user info or the ID token."""
    id_token = getattr(backend, "id_token", None) or {}
    value = response.get("email_verified", id_token.get("email_verified"))
    return value is True or value == "true"


class OIDCExceptionMiddleware(SocialAuthExceptionMiddleware):
    """
    Shows translated messages instead of the library's English ones, and
    sends a logged-in user (linking from the settings page) back there.
    """

    def get_message(self, request, exception):
        if isinstance(exception, AuthAssociationError):
            return _("This provider account is already linked to another user.")
        if isinstance(exception, AuthPolicyError):
            return _("This account is not allowed to log in.")
        return _("Login with the identity provider failed. Try again later.")

    def get_redirect_uri(self, request, exception):
        if request.user.is_authenticated:
            return reverse("babubi:user-settings")
        return super().get_redirect_uri(request, exception)


def oidc_linked(user):
    """Whether the user has a provider account linked."""
    return UserSocialAuth.objects.filter(user=user, provider="oidc").exists()


def can_unlink(user):
    """
    Unlinking must leave a way in: a password, and password login allowed.
    """
    return "password" in settings.LOGIN_METHODS and user.has_usable_password()


@require_POST
@oidc_login_required
def disconnect(request, backend):
    """Unlinks the provider account from the logged-in user, when allowed."""
    if not request.user.is_authenticated or not can_unlink(request.user):
        raise PermissionDenied
    return social_views.disconnect(request, backend)


@csrf_exempt
@require_POST
@never_cache
@oidc_login_required
def backchannel_logout(request):
    """
    OpenID Connect Back-Channel Logout 1.0: the provider posts a signed
    logout token, and every session of the user it names ends.
    """
    backend = load_backend(load_strategy(request), "oidc", redirect_uri=None)
    token = request.POST.get("logout_token", "")
    try:
        key = backend.find_valid_key(token)
        if key is None:
            raise jwt.InvalidSignatureError
        claims = jwt.decode(
            token,
            jwt.PyJWK(key).key,
            algorithms=[key["alg"]],
            audience=backend.setting("KEY"),
            issuer=backend.id_token_issuer(),
            leeway=backend.JWT_LEEWAY,
            options={"require": ["iat"]},
        )
    except (jwt.PyJWTError, ValueError, SocialAuthBaseException):
        return HttpResponseBadRequest()
    # Logout tokens never carry a nonce, which keeps ID tokens out. Logging
    # out by session ID alone (sid without sub) is not supported.
    events = claims.get("events")
    if (
        not isinstance(events, dict)
        or BACKCHANNEL_LOGOUT_EVENT not in events
        or "nonce" in claims
        or not claims.get("sub")
    ):
        return HttpResponseBadRequest()

    user_ids = {
        str(user_id)
        for user_id in UserSocialAuth.objects.filter(
            provider=backend.name, uid=claims["sub"]
        ).values_list("user_id", flat=True)
    }
    if user_ids:
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            if session.get_decoded().get(SESSION_KEY) in user_ids:
                session.delete()
    return HttpResponse()
