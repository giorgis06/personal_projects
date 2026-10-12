import importlib
import pkgutil

import femstudio.backends as backends_package
from femstudio.backends.base import SolverBackend

_registered: dict[str, SolverBackend] = {}
_discovered = False
_NOT_BACKENDS = {"base", "registry"}


class UnknownBackend(KeyError):
    pass


def register(backend: SolverBackend) -> None:
    if backend.name in _registered:
        raise ValueError(f"backend '{backend.name}' is already registered")
    _registered[backend.name] = backend


def _discover() -> None:
    """Import every backend module; each registers itself."""
    global _discovered
    if _discovered:
        return
    for module in pkgutil.iter_modules(backends_package.__path__):
        if module.name not in _NOT_BACKENDS:
            importlib.import_module(f"{backends_package.__name__}.{module.name}")
    _discovered = True


def get(name: str) -> SolverBackend:
    _discover()
    if name not in _registered:
        known = ", ".join(sorted(_registered)) or "none"
        raise UnknownBackend(f"no backend '{name}'; registered: {known}")
    return _registered[name]


def available() -> list[SolverBackend]:
    """Registered backends, ordered by name."""
    _discover()
    return sorted(_registered.values(), key=lambda b: b.name)
