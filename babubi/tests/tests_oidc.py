# -*- coding: utf-8 -*-
import json
import time
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase, override_settings
from django.utils import timezone
from requests import Response
from rest_framework.authtoken.models import Token
from social_django.models import UserSocialAuth

ISSUER = "https://idp.example.com/app"
CLIENT_ID = "babubi-client"
# One key for the whole run: the backend caches the provider's JWKS.
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = {
    **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key())),
    "kid": "test-key",
    "alg": "RS256",
    "use": "sig",
}
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
LOGOUT_EVENT = {"http://schemas.openid.net/event/backchannel-logout": {}}

OIDC_SETTINGS = {
    "SOCIAL_AUTH_OIDC_OIDC_ENDPOINT": ISSUER,
    "SOCIAL_AUTH_OIDC_KEY": CLIENT_ID,
    "SOCIAL_AUTH_OIDC_SECRET": "secret",
    "AXES_ENABLED": True,
}


def sign(claims, key=PRIVATE_KEY):
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})


class FakeProvider:
    """Answers the HTTP requests the OIDC backend makes to the provider."""

    def __init__(
        self,
        sub="sub-isaac",
        username="isaac",
        email="isaac@example.com",
        email_verified=True,
    ):
        self.sub = sub
        self.username = username
        self.email = email
        self.email_verified = email_verified
        self.nonce = None

    def __call__(self, method, url, **kwargs):
        documents = {
            f"{ISSUER}/.well-known/openid-configuration": {
                "issuer": ISSUER,
                "authorization_endpoint": f"{ISSUER}/authorize",
                "token_endpoint": f"{ISSUER}/token",
                "userinfo_endpoint": f"{ISSUER}/userinfo",
                "jwks_uri": f"{ISSUER}/jwks",
            },
            f"{ISSUER}/jwks": {"keys": [PUBLIC_JWK]},
            f"{ISSUER}/userinfo": {
                "sub": self.sub,
                "email": self.email,
                "email_verified": self.email_verified,
            },
        }
        if url == f"{ISSUER}/token":
            now = int(time.time())
            id_token = {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": self.sub,
                "iat": now,
                "exp": now + 300,
                "nonce": self.nonce,
                "preferred_username": self.username,
            }
            document = {
                "access_token": "access",
                "token_type": "Bearer",
                "id_token": sign(id_token),
            }
        else:
            document = documents[url]
        response = Response()
        response.status_code = 200
        response._content = json.dumps(document).encode()
        response.headers["Content-Type"] = "application/json"
        return response


class OIDCTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="isaac", password="password", email="isaac@example.com"
        )

    def log_in(self, provider, next_url="/welcome/"):
        with mock.patch("social_core.backends.base.requests.request", provider):
            response = self.client.post("/oidc/login/oidc/", {"next": next_url})
            query = parse_qs(urlsplit(response["Location"]).query)
            provider.nonce = query["nonce"][0]
            return self.client.get(
                "/oidc/complete/oidc/", {"state": query["state"][0], "code": "code"}
            )

    def link(self, user, sub):
        """A link as the backend stores it, keyed by the sub claim."""
        return UserSocialAuth.objects.create(
            user=user, provider="oidc", uid=sub, id_key="sub"
        )

    def assertTurnedAway(self, response, sub="sub-isaac"):
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        self.assertFalse(UserSocialAuth.objects.filter(uid=sub).exists())
        page = self.client.get("/login/")
        self.assertContains(page, "This account is not allowed to log in.")


@override_settings(LOGIN_METHODS=["oidc"], **OIDC_SETTINGS)
class OIDCLoginTestCase(OIDCTestCase):
    def test_known_user_logs_in(self):
        response = self.log_in(FakeProvider())
        self.assertRedirects(response, "/welcome/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/welcome/").status_code, 200)
        self.assertTrue(
            UserSocialAuth.objects.filter(user=self.user, uid="sub-isaac").exists()
        )

    def test_email_matches_without_case(self):
        response = self.log_in(FakeProvider(username="x", email="Isaac@Example.com"))
        self.assertRedirects(response, "/welcome/", fetch_redirect_response=False)

    def test_unverified_email_is_turned_away(self):
        self.assertTurnedAway(self.log_in(FakeProvider(email_verified=False)))
        self.assertTurnedAway(self.log_in(FakeProvider(email_verified="false")))

    def test_unknown_email_is_turned_away(self):
        self.assertTurnedAway(self.log_in(FakeProvider(email="guest@example.com")))
        self.assertTurnedAway(self.log_in(FakeProvider(email=None)))
        self.assertFalse(get_user_model().objects.filter(username="guest").exists())

    def test_user_without_email_is_turned_away(self):
        self.user.email = ""
        self.user.save()
        self.assertTurnedAway(self.log_in(FakeProvider(email="")))

    def test_shared_email_is_turned_away(self):
        get_user_model().objects.create_user(
            username="twin", password="password", email="isaac@example.com"
        )
        self.assertTurnedAway(self.log_in(FakeProvider()))

    @override_settings(OIDC_MATCH_BY="username")
    def test_username_mode(self):
        response = self.log_in(FakeProvider(username="Isaac", email="x@example.com"))
        self.assertRedirects(response, "/welcome/", fetch_redirect_response=False)
        self.assertTrue(UserSocialAuth.objects.filter(user=self.user).exists())
        self.client.logout()
        self.assertTurnedAway(
            self.log_in(FakeProvider(sub="sub-2", username="guest")), sub="sub-2"
        )

    def test_linked_account_logs_in_by_sub(self):
        self.link(self.user, "sub-isaac")
        response = self.log_in(FakeProvider(username="other", email="o@example.com"))
        self.assertRedirects(response, "/welcome/", fetch_redirect_response=False)

    def test_inactive_user_is_turned_away(self):
        self.user.is_active = False
        self.user.save()
        response = self.log_in(FakeProvider())
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

    def test_expired_user_is_turned_away(self):
        self.user.settings.access_expires = timezone.now() - timezone.timedelta(1)
        self.user.settings.save()
        response = self.log_in(FakeProvider())
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

    def test_begin_goes_to_the_provider(self):
        with mock.patch("social_core.backends.base.requests.request", FakeProvider()):
            response = self.client.post("/oidc/login/oidc/")
        location = urlsplit(response["Location"])
        self.assertEqual(
            f"https://{location.netloc}{location.path}", f"{ISSUER}/authorize"
        )
        query = parse_qs(location.query)
        self.assertEqual(query["client_id"], [CLIENT_ID])
        self.assertEqual(query["scope"], ["openid profile email"])
        self.assertIn("code_challenge", query)


class LoginMethodsTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-user", password="password"
        )

    def test_password_only_by_default(self):
        page = self.client.get("/login/")
        self.assertContains(page, 'name="login"')
        self.assertNotContains(page, 'name="oidc-login"')
        self.assertEqual(self.client.post("/oidc/login/oidc/").status_code, 404)
        self.assertEqual(self.client.get("/reset/").status_code, 200)

    @override_settings(LOGIN_METHODS=["password", "oidc"], **OIDC_SETTINGS)
    def test_password_and_oidc(self):
        page = self.client.get("/login/?next=/welcome/")
        self.assertContains(page, 'name="login"')
        self.assertContains(page, "Log in with single sign-on")
        self.assertContains(page, 'action="/oidc/login/oidc/"')
        self.assertContains(page, 'value="/welcome/"', count=2)
        self.assertEqual(self.client.get("/reset/").status_code, 200)

    def test_methods_follow_the_setting_order(self):
        for methods, first in (
            (["password", "oidc"], 'name="login"'),
            (["oidc", "password"], 'name="oidc-login"'),
        ):
            with self.subTest(methods=methods), self.settings(
                LOGIN_METHODS=methods, **OIDC_SETTINGS
            ):
                page = self.client.get("/login/").content.decode()
                buttons = sorted(('name="login"', 'name="oidc-login"'), key=page.index)
                self.assertEqual(buttons[0], first)
                # The first method gets the primary button, the other the outline.
                self.assertEqual(page.count("btn-primary"), 1)
                self.assertLess(
                    page.index("btn-primary"), page.index("btn-outline-primary")
                )

    @override_settings(
        LOGIN_METHODS=["password", "oidc"], OIDC_PROVIDER_NAME="Example ID"
    )
    def test_provider_name_on_the_button(self):
        self.assertContains(self.client.get("/login/"), "Log in with Example ID")

    @override_settings(LOGIN_METHODS=["oidc"], **OIDC_SETTINGS)
    def test_oidc_only(self):
        page = self.client.get("/login/")
        self.assertContains(page, 'name="oidc-login"')
        self.assertNotContains(page, 'name="login"')
        self.assertNotContains(page, 'name="reset"')

        response = self.client.post(
            "/login/", {"username": "admin-user", "password": "password"}
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get("/welcome/").status_code, 302)

        for url in ("/admin/login/", "/api/auth/login/", "/reset/", "/reset/done/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTrue(response["Location"].startswith("/login/"))
        response = self.client.post(
            "/admin/login/", {"username": "admin-user", "password": "password"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/welcome/").status_code, 302)

    @override_settings(LOGIN_METHODS=["oidc"], **OIDC_SETTINGS)
    def test_api_tokens_still_work(self):
        token = Token.objects.create(user=self.user)
        response = self.client.get(
            "/api/children/", HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        self.assertEqual(response.status_code, 200)


@override_settings(LOGIN_METHODS=["oidc"], **OIDC_SETTINGS)
class BackchannelLogoutTestCase(TestCase):
    url = "/oidc/logout/backchannel/"

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="isaac")
        UserSocialAuth.objects.create(user=self.user, provider="oidc", uid="sub-isaac")
        self.other = get_user_model().objects.create_user(username="anna")
        self.client.force_login(self.user)
        self.other_client = self.client_class()
        self.other_client.force_login(self.other)

    def claims(self, **changes):
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "sub-isaac",
            "iat": int(time.time()),
            "jti": "logout-1",
            "events": LOGOUT_EVENT,
        }
        claims.update(changes)
        return {k: v for k, v in claims.items() if v is not None}

    def post(self, token):
        with mock.patch("social_core.backends.base.requests.request", FakeProvider()):
            return self.client_class().post(self.url, {"logout_token": token})

    def test_logout_ends_the_user_sessions(self):
        response = self.post(sign(self.claims()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/welcome/").status_code, 302)
        self.assertEqual(self.other_client.get("/welcome/").status_code, 200)
        self.assertEqual(Session.objects.count(), 1)

    def test_invalid_tokens_are_rejected(self):
        cases = {
            "signature": sign(self.claims(), key=OTHER_KEY),
            "issuer": sign(self.claims(iss="https://other.example.com")),
            "audience": sign(self.claims(aud="other-client")),
            "event": sign(self.claims(events={})),
            "nonce": sign(self.claims(nonce="n")),
            "sid only": sign(self.claims(sub=None, sid="session")),
            "garbage": "not-a-token",
        }
        for name, token in cases.items():
            with self.subTest(name):
                self.assertEqual(self.post(token).status_code, 400)
        self.assertEqual(self.client.get("/welcome/").status_code, 200)

    @override_settings(LOGIN_METHODS=["password"])
    def test_hidden_without_oidc(self):
        self.assertEqual(self.post(sign(self.claims())).status_code, 404)
