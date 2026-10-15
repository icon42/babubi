# -*- coding: utf-8 -*-
import os
import tempfile

from django.test import TestCase, override_settings


class BrandingTestCase(TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        override = override_settings(BRANDING_DIR=self.dir.name)
        override.enable()
        self.addCleanup(override.disable)

    def add(self, name, content):
        with open(os.path.join(self.dir.name, name), "w") as f:
            f.write(content)

    def test_defaults_without_files(self):
        page = self.client.get("/login/")
        self.assertContains(page, "babubi/logo/logo.")
        self.assertContains(page, "babubi/logo/logo-dark.")
        self.assertNotContains(page, "/branding/")

    @override_settings(BRANDING_DIR=None)
    def test_disabled(self):
        self.assertEqual(self.client.get("/branding/logo.svg").status_code, 404)

    def test_custom_logo_icon_and_css(self):
        self.add("logo.svg", "<svg/>")
        self.add("icon.svg", "<svg/>")
        self.add("custom.css", "body { color: red; }")
        page = self.client.get("/login/")
        self.assertContains(page, "/branding/logo.svg?v=")
        self.assertContains(page, "/branding/icon.svg?v=")
        self.assertContains(
            page, '<link rel="stylesheet" href="/branding/custom.css?v='
        )
        # Without logo-dark.svg the custom logo serves dark backgrounds too.
        self.assertNotContains(page, "babubi/logo/logo-dark.")

    def test_custom_dark_logo(self):
        self.add("logo.svg", "<svg/>")
        self.add("logo-dark.svg", "<svg/>")
        page = self.client.get("/login/")
        self.assertContains(page, "/branding/logo-dark.svg?v=")

    def test_serves_files_publicly(self):
        self.add("custom.css", "body { color: red; }")
        response = self.client.get("/branding/custom.css")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"body { color: red; }")

    def test_svg_cannot_run_scripts(self):
        self.add("logo.svg", "<svg/>")
        response = self.client.get("/branding/logo.svg")
        self.assertEqual(response.status_code, 200)
        self.assertIn("default-src 'none'", response["Content-Security-Policy"])

    def test_only_known_names(self):
        self.add("secret.txt", "secret")
        self.assertEqual(self.client.get("/branding/secret.txt").status_code, 404)
        self.assertEqual(self.client.get("/branding/icon.svg").status_code, 404)
