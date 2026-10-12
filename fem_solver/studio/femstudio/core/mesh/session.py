from collections.abc import Callable, Iterator
from contextlib import contextmanager

import gmsh


@contextmanager
def gmsh_session(on_log: Callable[[str], None] | None = None) -> Iterator[None]:
    """A fresh gmsh model; gmsh log lines go to `on_log` when the block ends."""
    owned = not gmsh.isInitialized()
    if owned:
        gmsh.initialize(interruptible=False)
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.logger.start()
    gmsh.model.add("studio")
    try:
        yield
    finally:
        lines = gmsh.logger.get()
        gmsh.logger.stop()
        gmsh.model.remove()
        if owned:
            gmsh.finalize()
        if on_log is not None:
            for line in lines:
                on_log(line)
