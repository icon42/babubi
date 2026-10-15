# -*- coding: utf-8 -*-
import os
import tempfile

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.authtoken.models import Token

from babubi.views import media


class MediaTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media_dir.name)
        cls.override.enable()
        os.makedirs(os.path.join(cls.media_dir.name, "children"))
        with open(os.path.join(cls.media_dir.name, "children", "pic.jpg"), "wb") as f:
            f.write(b"picture")
        # A file beside MEDIA_ROOT that no URL may reach.
        cls.outside = os.path.join(
            os.path.dirname(cls.media_dir.name), "babubi-outside.txt"
        )
        with open(cls.outside, "w") as f:
            f.write("secret")

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.media_dir.cleanup()
        os.remove(cls.outside)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="parent")
        cls.token = Token.objects.create(user=cls.user)

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get("/media/children/pic.jpg")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_signed_in_user_gets_file(self):
        self.client.force_login(self.user)
        response = self.client.get("/media/children/pic.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"picture")

    def test_api_token_gets_file(self):
        response = self.client.get(
            "/media/children/pic.jpg", HTTP_AUTHORIZATION="Token " + self.token.key
        )
        self.assertEqual(response.status_code, 200)

    def test_bad_token_is_sent_to_login(self):
        response = self.client.get(
            "/media/children/pic.jpg", HTTP_AUTHORIZATION="Token nope"
        )
        self.assertEqual(response.status_code, 302)

    def test_missing_file(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/media/children/none.jpg").status_code, 404)
        self.assertEqual(self.client.get("/media/children/").status_code, 404)

    def test_path_outside_media_root(self):
        self.client.force_login(self.user)
        for path in (
            "/media/../babubi-outside.txt",
            "/media/%2e%2e/babubi-outside.txt",
            "/media/children/..%2f..%2fbabubi-outside.txt",
        ):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_view_refuses_path_outside_media_root(self):
        # The URL layer already normalises "..", so call the view directly.
        request = RequestFactory().get("/")
        request.user = self.user
        with self.assertRaises(Http404):
            media(request, "../babubi-outside.txt")
