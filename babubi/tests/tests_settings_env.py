# -*- coding: utf-8 -*-
import importlib
import os
from unittest import mock

from django.test import SimpleTestCase

from babubi.settings import base


class EnvironmentSettingsTestCase(SimpleTestCase):
    def tearDown(self):
        importlib.reload(base)

    def test_locale_defaults(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("LANGUAGE_CODE", None)
            os.environ.pop("TIME_ZONE", None)
            importlib.reload(base)
        self.assertEqual(base.LANGUAGE_CODE, "en-US")
        self.assertEqual(base.TIME_ZONE, "UTC")

    def test_locale_from_environment(self):
        with mock.patch.dict(
            os.environ, {"LANGUAGE_CODE": "ca", "TIME_ZONE": "Europe/Paris"}
        ):
            importlib.reload(base)
        self.assertEqual(base.LANGUAGE_CODE, "ca")
        self.assertEqual(base.TIME_ZONE, "Europe/Paris")
