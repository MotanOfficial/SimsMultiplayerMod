"""Monkey-patch Override for Sims 4 methods (host / joiner / all).

When a deep session becomes active, matching overrides replace live game
methods. On disconnect they restore the originals. Pure Python; game imports
are resolved lazily from the target method objects.
"""

import enum
import sys


class Role(enum.IntEnum):
    JOINER = 0
    HOST = 1
    ALL = 2


class Override(object):
    """Replace a game method for the duration of a deep multiplayer session."""

    _registry = []

    def __init__(self, method, role=Role.ALL, enabled_while_traveling=True, target=None, name=None):
        self._role = role
        self._enabled_while_traveling = enabled_while_traveling
        self._active = False
        self._wrapped = None
        self._original = None
        self._target = None
        self._name = None
        if target is not None:
            self._target = target
            self._name = name or method.__name__
            self._original = getattr(target, self._name)
        else:
            self._resolve_target(method)
        Override._registry.append(self)

    def _resolve_target(self, method):
        module = sys.modules.get(method.__module__)
        if module is None:
            raise RuntimeError("module %r not loaded for override" % method.__module__)
        meth_name = method.__name__
        parts = [p for p in method.__qualname__.split(".") if p != "<locals>"]
        target = module
        for part in parts[:-1]:
            if not hasattr(target, part):
                # Nested test helpers / unbound paths: fall back to searching
                # for a class that currently owns this function object.
                owner = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name, None)
                    if isinstance(attr, type) and getattr(attr, meth_name, None) is method:
                        owner = attr
                        break
                if owner is None:
                    raise AttributeError("cannot resolve override target for %s" % method.__qualname__)
                target = owner
                break
            target = getattr(target, part)
        if not hasattr(target, meth_name):
            raise AttributeError("cannot resolve override target for %s" % method.__qualname__)
        self._target = target
        self._name = meth_name
        self._original = getattr(target, meth_name)

    def __call__(self, func):
        self._func = func

        def _wrapped(*args, **kwargs):
            return self._func(self._original, *args, **kwargs)

        self._wrapped = _wrapped
        return _wrapped

    def should_install(self, is_host):
        if self._role == Role.ALL:
            return True
        if self._role == Role.HOST:
            return bool(is_host)
        return not bool(is_host)

    def install(self, is_host):
        if self._active or self._wrapped is None:
            return False
        if not self.should_install(is_host):
            return False
        setattr(self._target, self._name, self._wrapped)
        self._active = True
        return True

    def uninstall(self):
        if not self._active:
            return False
        setattr(self._target, self._name, self._original)
        self._active = False
        return True

    @classmethod
    def install_all(cls, is_host):
        installed = 0
        for override in cls._registry:
            if override.install(is_host):
                installed += 1
        return installed

    @classmethod
    def uninstall_all(cls):
        removed = 0
        for override in cls._registry:
            if override.uninstall():
                removed += 1
        return removed

    @classmethod
    def clear_registry(cls):
        """Test helper: drop registered overrides without touching game state."""
        for override in list(cls._registry):
            override.uninstall()
        cls._registry[:] = []
