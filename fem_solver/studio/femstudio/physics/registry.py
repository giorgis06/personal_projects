import importlib
import pkgutil

import femstudio.physics as physics_package
from femstudio.physics.base import ProblemType

_registered: dict[str, ProblemType] = {}
_discovered = False


class UnknownProblemType(KeyError):
    pass


def register(problem_type: ProblemType) -> None:
    if problem_type.name in _registered:
        raise ValueError(f"problem type '{problem_type.name}' is already registered")
    _registered[problem_type.name] = problem_type


def _discover() -> None:
    """Import every sub-package of `physics`; each registers its own problem type."""
    global _discovered
    if _discovered:
        return
    for module in pkgutil.iter_modules(physics_package.__path__):
        if module.ispkg:
            importlib.import_module(f"{physics_package.__name__}.{module.name}")
    _discovered = True


def get(name: str) -> ProblemType:
    _discover()
    if name not in _registered:
        known = ", ".join(sorted(_registered)) or "none"
        raise UnknownProblemType(f"no problem type '{name}'; registered: {known}")
    return _registered[name]


def available() -> list[ProblemType]:
    _discover()
    return sorted(_registered.values(), key=lambda p: p.name)
