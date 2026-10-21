# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save


class DashboardConfig(AppConfig):
    name = "dashboard"

    def ready(self):
        from django.apps import apps

        from . import versions

        # Every core model of a child, the child itself, and Babubi's own
        # records shown on a dashboard: a change to any bumps its version.
        watched = [
            model
            for model in apps.get_app_config("core").get_models()
            if model.__name__ == "Child"
            or any(field.name == "child" for field in model._meta.fields)
        ]
        watched += [
            apps.get_model("dashboard", name)
            for name in ("ChildProfile", "TimerProfile", "DashboardLayout")
        ]
        for model in watched:
            for signal in (post_save, post_delete):
                signal.connect(
                    versions.on_change,
                    sender=model,
                    dispatch_uid="dashboard-version-{}-{}".format(
                        model._meta.label, signal is post_save
                    ),
                )
