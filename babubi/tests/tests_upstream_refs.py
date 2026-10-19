# -*- coding: utf-8 -*-
import os
import re

from django.conf import settings
from django.test import SimpleTestCase

# Code merged from upstream still names the old package. Git merges such new
# lines without a conflict, and they only break at runtime, so look for them:
# imports, dotted paths, template paths and URL namespaces.
OLD_PACKAGE = re.compile(r"\b(?:from|import)\s+babybuddy\b|[\"']babybuddy[.:/]")
EXTENSIONS = (".py", ".html", ".txt")
SKIPPED_DIRS = {".git", "_mat", "node_modules", "static"}


class UpstreamReferencesTestCase(SimpleTestCase):
    def test_no_references_to_the_old_package(self):
        found = []
        for root, dirs, files in os.walk(settings.BASE_DIR):
            dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
            for name in files:
                if not name.endswith(EXTENSIONS):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as file:
                    for number, line in enumerate(file, 1):
                        if OLD_PACKAGE.search(line):
                            relative = os.path.relpath(path, settings.BASE_DIR)
                            found.append(f"{relative}:{number}: {line.strip()}")
        if found:
            self.fail("Rename babybuddy to babubi in:\n" + "\n".join(found))
