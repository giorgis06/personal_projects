import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.field import Field

SOLUTION_FILE = "solution.csv"
RUN_FILE = "run.json"
SOLUTION_HEADER = ["node_tag", "u"]


class ResultError(ValueError):
    """The result folder is missing, incomplete or not in the contract's format."""


@dataclass(frozen=True)
class RunInfo:
    status: str
    iterations: int | None
    residual: float | None
    timings: dict[str, float] = field(default_factory=dict)
    message: str = ""


def _number(data: dict, key: str, kind: type) -> int | float | None:
    value = data[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResultError(f"{RUN_FILE}: '{key}' is not a number")
    return kind(value)


def read_run_info(result_dir: Path) -> RunInfo:
    path = Path(result_dir) / RUN_FILE
    if not path.is_file():
        raise ResultError(f"{RUN_FILE} is missing from {result_dir}")
    try:
        data = json.loads(path.read_text())
        timings = data["timings"]
        if not isinstance(timings, dict):
            raise ResultError(f"{RUN_FILE}: 'timings' is not an object")
        if not isinstance(data["status"], str) or not isinstance(data["message"], str):
            raise ResultError(f"{RUN_FILE}: 'status' and 'message' must be text")
        return RunInfo(
            status=data["status"],
            iterations=_number(data, "iterations", int),
            residual=_number(data, "residual", float),
            timings={str(k): float(v) for k, v in timings.items()},
            message=data["message"],
        )
    except json.JSONDecodeError as error:
        raise ResultError(f"{RUN_FILE} is not valid JSON: {error}") from error
    except KeyError as error:
        raise ResultError(f"{RUN_FILE} lacks {error}") from error
    except (TypeError, ValueError) as error:
        if isinstance(error, ResultError):
            raise
        raise ResultError(f"{RUN_FILE} is malformed: {error}") from error


def read_solution(result_dir: Path, mesh: MeshData, *, name: str, unit: str) -> Field:
    """Match each row's node tag to the mesh, so row order carries no meaning."""
    path = Path(result_dir) / SOLUTION_FILE
    if not path.is_file():
        raise ResultError(f"{SOLUTION_FILE} is missing from {result_dir}")
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != SOLUTION_HEADER:
        raise ResultError(f"{SOLUTION_FILE} header must be {','.join(SOLUTION_HEADER)}")
    tags, values = [], []
    for number, row in enumerate(rows[1:], start=2):
        try:
            tag, value = int(row[0]), float(row[1])
        except (ValueError, IndexError) as error:
            raise ResultError(f"{SOLUTION_FILE} line {number} is not 'tag,value'") from error
        if not math.isfinite(value):
            raise ResultError(f"{SOLUTION_FILE} line {number}: value is not finite")
        tags.append(tag)
        values.append(value)
    tags_array = np.array(tags, dtype=np.int64)
    if len(np.unique(tags_array)) != len(tags_array):
        raise ResultError(f"{SOLUTION_FILE} repeats a node tag")
    order = np.argsort(mesh.node_tags)
    sorted_tags = mesh.node_tags[order]
    position = np.searchsorted(sorted_tags, tags_array).clip(max=len(sorted_tags) - 1)
    if len(sorted_tags) and not np.array_equal(sorted_tags[position], tags_array):
        raise ResultError(f"{SOLUTION_FILE} has a node tag the mesh does not")
    if len(tags_array) != mesh.n_nodes:
        raise ResultError(
            f"{SOLUTION_FILE} has {len(tags_array)} rows for {mesh.n_nodes} mesh nodes"
        )
    result = np.empty(mesh.n_nodes)
    result[order[position]] = values
    return Field(name, result, unit)
