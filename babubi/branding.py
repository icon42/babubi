# -*- coding: utf-8 -*-
"""
Logo, icon and extra CSS that a deployment can supply as files in
BRANDING_DIR, in place of Babubi's own.
"""

import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.templatetags.static import static
from django.urls import reverse

# The only files read from BRANDING_DIR; nothing else there is ever served.
FILES = ("logo.svg", "logo-dark.svg", "icon.svg", "custom.css")


def _custom_path(name):
    if not settings.BRANDING_DIR:
        return None
    path = os.path.join(settings.BRANDING_DIR, name)
    return path if os.path.isfile(path) else None


def _custom_url(name):
    path = _custom_path(name)
    if path is None:
        return None
    # The modification time busts browser caches when the file changes.
    version = int(os.path.getmtime(path))
    return "{}?v={}".format(reverse("babubi:branding", args=[name]), version)


def context(request):
    logo = _custom_url("logo.svg")
    return {
        "branding": {
            "logo_url": logo or static("babubi/logo/logo.svg"),
            # For dark backgrounds; a custom logo without a dark version is
            # used on both rather than mixing it with Babubi's own.
            "logo_dark_url": _custom_url("logo-dark.svg")
            or logo
            or static("babubi/logo/logo-dark.svg"),
            "icon_url": _custom_url("icon.svg") or static("babubi/logo/icon.svg"),
            "custom_css_url": _custom_url("custom.css"),
        }
    }


def serve(request, name):
    if name not in FILES:
        raise Http404
    path = _custom_path(name)
    if path is None:
        raise Http404
    response = FileResponse(open(path, "rb"))
    if name.endswith(".svg"):
        # An SVG opened directly could run scripts in Babubi's origin.
        response["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'"
        )
    return response
