import json

import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.reader import ResultError, read_run_info, read_solution

GOOD_RUN = {
    "status": "success",
    "iterations": 42,
    "residual": 3.5e-11,
    "timings": {"assemble": 0.5, "solve": 1.25},
    "message": "",
}


@pytest.fixture
def mesh():
    # tags are not 1..N and not in order, so a row-order assumption would be caught
    return MeshData(
        nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
        node_tags=np.array([30, 10, 20]),
        triangles=np.array([[0, 1, 2]]),
        edges=np.empty((0, 2), dtype=int),
        regions={},
        boundaries={},
    )


def write_csv(folder, text):
    (folder / "solution.csv").write_text(text)


def write_run(folder, **changes):
    data = {**GOOD_RUN, **changes}
    (folder / "run.json").write_text(json.dumps({k: v for k, v in data.items() if v != "DROP"}))


def test_values_follow_the_node_tags_not_the_row_order(tmp_path, mesh):
    write_csv(tmp_path, "node_tag,u\n10,1.5\n20,2.5\n30,3.5\n")
    field = read_solution(tmp_path, mesh)
    np.testing.assert_array_equal(field.values, [3.5, 1.5, 2.5])
    assert (field.name, field.unit, field.location) == ("u", "V", "node")


def test_run_info(tmp_path):
    write_run(tmp_path)
    info = read_run_info(tmp_path)
    assert (info.status, info.iterations, info.residual) == ("success", 42, 3.5e-11)
    assert info.timings == {"assemble": 0.5, "solve": 1.25}


def test_run_info_allows_null_iterations_and_residual(tmp_path):
    write_run(tmp_path, iterations=None, residual=None, status="failed", message="singular")
    info = read_run_info(tmp_path)
    assert (info.iterations, info.residual, info.message) == (None, None, "singular")


@pytest.mark.parametrize(
    "text",
    [
        "tag,u\n10,1\n20,2\n30,3\n",
        "node_tag,u\n10,1\n20,2\n",
        "node_tag,u\n10,1\n20,2\n30,3\n40,4\n",
        "node_tag,u\n10,1\n10,2\n30,3\n",
        "node_tag,u\n10,1\n20,2\n99,3\n",
        "node_tag,u\n10,1\n20,two\n30,3\n",
        "node_tag,u\n10,1\n20,nan\n30,3\n",
        "node_tag,u\n10,1\n20,inf\n30,3\n",
        "node_tag,u\n10,1\n20\n30,3\n",
        "",
    ],
    ids=[
        "bad_header",
        "missing_row",
        "extra_row",
        "repeated_tag",
        "unknown_tag",
        "not_a_number",
        "nan",
        "inf",
        "short_row",
        "empty_file",
    ],
)
def test_malformed_solution_is_refused(tmp_path, mesh, text):
    write_csv(tmp_path, text)
    with pytest.raises(ResultError):
        read_solution(tmp_path, mesh)


def test_missing_files(tmp_path, mesh):
    with pytest.raises(ResultError, match="solution.csv is missing"):
        read_solution(tmp_path, mesh)
    with pytest.raises(ResultError, match="run.json is missing"):
        read_run_info(tmp_path)


@pytest.mark.parametrize("key", ["status", "iterations", "residual", "timings", "message"])
def test_run_info_needs_every_key(tmp_path, key):
    write_run(tmp_path, **{key: "DROP"})
    with pytest.raises(ResultError, match=key):
        read_run_info(tmp_path)


@pytest.mark.parametrize(
    "changes",
    [{"iterations": "many"}, {"timings": [1, 2]}, {"status": 1}, {"residual": True}],
)
def test_run_info_with_wrong_types(tmp_path, changes):
    write_run(tmp_path, **changes)
    with pytest.raises(ResultError):
        read_run_info(tmp_path)


def test_run_info_not_json(tmp_path):
    (tmp_path / "run.json").write_text("{nope")
    with pytest.raises(ResultError, match="not valid JSON"):
        read_run_info(tmp_path)
