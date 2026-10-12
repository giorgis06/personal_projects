from collections.abc import Callable, Iterator
from contextlib import contextmanager

import gmsh

TOUCHED_OPTIONS = ("General.Terminal", "Mesh.MeshSizeMax")


@contextmanager
def gmsh_session(on_log: Callable[[str], None] | None = None) -> Iterator[None]:
    """A fresh gmsh model; gmsh log lines go to `on_log` when the block ends.

    A gmsh session the caller already owns keeps its models and the options this code touches.
    """
    owned = not gmsh.isInitialized()
    if owned:
        gmsh.initialize(interruptible=False)
    previous = gmsh.model.getCurrent()
    models = set(gmsh.model.list())
    options = {name: gmsh.option.getNumber(name) for name in TOUCHED_OPTIONS}
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.logger.start()
    gmsh.model.add("studio")
    try:
        yield
    finally:
        lines = gmsh.logger.get()
        gmsh.logger.stop()
        for name in set(gmsh.model.list()) - models:
            gmsh.model.setCurrent(name)
            gmsh.model.remove()
        if owned:
            gmsh.finalize()
        else:
            gmsh.model.setCurrent(previous)
            for name, value in options.items():
                gmsh.option.setNumber(name, value)
        if on_log is not None:
            for line in lines:
                on_log(line)
