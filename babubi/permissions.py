# -*- coding: utf-8 -*-
"""
The permissions backend that completes the user form's matrix (babubi/roles.py):
the kinds covered by the "All" flags of the user's settings, and what follows
from the kinds a user reads or writes (children, tags and timers). Django's
ModelBackend keeps answering for the permissions stored as such.
"""

from django.contrib.auth.backends import BaseBackend

from babubi import roles


class RoleBackend(BaseBackend):
    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, "_role_perm_cache"):
            reads, writes, read_all, write_all = roles.effective(user_obj)
            granted = roles.derived(reads, writes)
            if read_all:
                granted |= roles.perms(roles.ENTRY_TYPES, roles.READ_ACTIONS)
            if write_all:
                granted |= roles.perms(roles.ENTRY_TYPES, roles.WRITE_ACTIONS)
            user_obj._role_perm_cache = frozenset(granted)
        return user_obj._role_perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)
