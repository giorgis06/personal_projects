import json
import re

import meshio
import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.expressions.evaluate import evaluate
from femstudio.core.expressions.grammar import parse
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.scene.boundary import Between, Boundary, BoundaryCondition
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Rectangle
from femstudio.physics import registry
from femstudio.physics.base import ProblemError, SolverSettings

# The example in ORCHESTRATOR.md under "Solver contract", copied literally.
EPSILON_0 = 8.8541878128e-12  # F/m, from CODATA, written out here independently of the code
CONTRACT_EXAMPLE = {
    "schema_version": 1,
    "problem_type": "electrostatics",
    "mesh": "mesh.msh",
    "regions": {
        "glass": {"epsilon": [[4.0, 0.0], [0.0, 4.0]]},
        "air": {"epsilon": [[1.0, 0.0], [0.0, 1.0]]},
    },
    "source": {"rho": "(exp(-((x-1)^2 + y^2)/0.02)) / 8.8541878128e-12"},
    "boundaries": {
        "inner_electrode": {"kind": "dirichlet", "g": "5*cos(theta)"},
        "outer_wall": {"kind": "dirichlet", "g": "0"},
    },
    "solver": {"method": "cg", "tolerance": 1e-10, "max_iterations": 10000},
    "output": "result",
}


@pytest.fixture(scope="module")
def electrostatics():
    return registry.get("electrostatics")


def make_run(tmp_path, scene, size=0.2):
    mesh = mesh_scene(scene, size, tmp_path / "mesh.msh")
    return mesh, tmp_path


def contract_scene():
    scene = capacitor_scene()
    scene.boundaries[0].condition.values["g"] = "5*cos(theta)"
    scene.source["rho"] = "exp(-((x-1)^2 + y^2)/0.02)"
    return scene


def test_written_file_is_the_contract_example(tmp_path, electrostatics):
    scene = contract_scene()
    mesh, folder = make_run(tmp_path, scene)
    path = electrostatics.write_problem(scene, mesh, folder)
    assert path == folder / "problem.json"
    assert json.loads(path.read_text()) == CONTRACT_EXAMPLE


def test_names_in_the_file_are_physical_groups_of_the_mesh(tmp_path, electrostatics):
    scene = contract_scene()
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    groups = {
        name: int(dim) for name, (_, dim) in meshio.read(folder / "mesh.msh").field_data.items()
    }
    assert {n for n in document["regions"]} == {n for n, d in groups.items() if d == 2}
    assert {n for n in document["boundaries"]} == {n for n, d in groups.items() if d == 1}


def test_every_expression_and_tensor_in_the_file_is_valid(tmp_path, electrostatics):
    scene = contract_scene()
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    for text in document["source"].values():
        parse(text)
    for condition in document["boundaries"].values():
        for key, value in condition.items():
            if key != "kind":
                parse(value)
    for region in document["regions"].values():
        (a, b), (c, d) = region["epsilon"]
        assert a * d - b * c > 0 and b == c


def test_solver_settings_are_written(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    settings = SolverSettings(method="cg", tolerance=1e-6, max_iterations=50)
    path = electrostatics.write_problem(scene, mesh, folder, settings)
    assert json.loads(path.read_text())["solver"] == {
        "method": "cg",
        "tolerance": 1e-6,
        "max_iterations": 50,
    }


def test_scalar_permittivity_is_written_as_an_isotropic_tensor(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.regions[0].material["epsilon"] = 2.5
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert document["regions"]["glass"]["epsilon"] == [[2.5, 0.0], [0.0, 2.5]]


def test_missing_source_uses_the_field_default(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.source = {}
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert evaluate(document["source"]["rho"], 0.0, 0.0) == 0.0


def test_boundary_without_condition_is_insulating(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries[1].condition = None
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert document["boundaries"]["outer_wall"] == {"kind": "neumann", "g": "0"}


def test_interface_without_condition_is_left_out(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries.append(Boundary("interface", Between("glass", "air")))
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert "interface" not in document["boundaries"]
    assert "interface" in mesh.boundaries


def test_default_boundary_is_written_under_its_reserved_name(tmp_path, electrostatics):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    scene = Scene(
        "electrostatics",
        [square],
        [Region("air", square, {"epsilon": 1.0})],
        default_boundary=BoundaryCondition("dirichlet", {"g": "0"}),
    )
    mesh, folder = make_run(tmp_path, scene, 0.25)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert document["boundaries"] == {"default_boundary": {"kind": "dirichlet", "g": "0"}}


def test_default_boundary_is_left_out_when_no_edge_needs_it(tmp_path, electrostatics):
    scene = contract_scene()
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    mesh, folder = make_run(tmp_path, scene)
    document = json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())
    assert "default_boundary" not in document["boundaries"]


def test_scene_with_errors_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    scene.regions[0].material.clear()
    with pytest.raises(ProblemError, match="region 'glass'"):
        electrostatics.write_problem(scene, mesh, folder)
    assert not (folder / "problem.json").exists()


def test_unknown_kind_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    scene.boundaries[0].condition = BoundaryCondition("periodic", {})
    with pytest.raises(ProblemError, match="kind 'periodic'"):
        electrostatics.write_problem(scene, mesh, folder)


def test_missing_mesh_file_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    (folder / "mesh.msh").unlink()
    with pytest.raises(ProblemError, match=re.escape("mesh.msh is not in")):
        electrostatics.write_problem(scene, mesh, folder)


def test_name_missing_from_the_mesh_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    scene.regions[0].name = "porcelain"
    with pytest.raises(ProblemError, match="region 'porcelain' is not in the mesh"):
        electrostatics.write_problem(scene, mesh, folder)


def test_mesh_with_default_group_but_scene_without_one_is_refused(tmp_path, electrostatics):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    scene = Scene(
        "electrostatics",
        [square],
        [Region("air", square, {"epsilon": 1.0})],
        default_boundary=BoundaryCondition("dirichlet", {"g": "0"}),
    )
    mesh, folder = make_run(tmp_path, scene, 0.25)
    scene.default_boundary = None
    with pytest.raises(ProblemError, match="outer edges the scene gives no condition"):
        electrostatics.write_problem(scene, mesh, folder)


def written(tmp_path, electrostatics, scene, size=0.2):
    mesh, folder = make_run(tmp_path, scene, size)
    return json.loads(electrostatics.write_problem(scene, mesh, folder).read_text())


def test_charge_density_is_divided_by_epsilon_0(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.source["rho"] = "1"
    document = written(tmp_path, electrostatics, scene)
    assert evaluate(document["source"]["rho"], 0.0, 0.0) == pytest.approx(1 / EPSILON_0, rel=1e-9)


def test_charge_density_keeps_its_spatial_shape_when_scaled(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.source["rho"] = "x + 2*y"
    document = written(tmp_path, electrostatics, scene)
    assert evaluate(document["source"]["rho"], 3.0, 1.0) == pytest.approx(5.0 / EPSILON_0, rel=1e-9)


def test_surface_charge_is_divided_by_epsilon_0(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries[1].condition = BoundaryCondition("neumann", {"g": "2"})
    boundary = written(tmp_path, electrostatics, scene)["boundaries"]["outer_wall"]
    assert boundary["kind"] == "neumann"
    assert evaluate(boundary["g"], 0.0, 0.0) == pytest.approx(2 / EPSILON_0, rel=1e-9)


def test_dirichlet_potential_is_written_unchanged(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries[0].condition.values["g"] = "5"
    boundary = written(tmp_path, electrostatics, scene)["boundaries"]["inner_electrode"]
    assert boundary == {"kind": "dirichlet", "g": "5"}


def test_robin_writes_kappa_and_g_as_kappa_times_the_reference_potential(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries[1].condition = BoundaryCondition("robin", {"kappa": "2", "u_ref": "5"})
    boundary = written(tmp_path, electrostatics, scene)["boundaries"]["outer_wall"]
    assert set(boundary) == {"kind", "kappa", "g"}
    assert boundary["kind"] == "robin"
    assert evaluate(boundary["kappa"], 0.0, 0.0) == 2.0
    assert evaluate(boundary["g"], 0.0, 0.0) == 10.0


def test_robin_g_follows_the_position_when_kappa_does(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries[1].condition = BoundaryCondition("robin", {"kappa": "x + 3", "u_ref": "y"})
    boundary = written(tmp_path, electrostatics, scene)["boundaries"]["outer_wall"]
    assert evaluate(boundary["g"], 2.0, 4.0) == pytest.approx((2 + 3) * 4)


def test_scalar_permittivity_that_is_not_positive_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    for value in (-1.0, 0.0, float("nan"), float("inf")):
        scene.regions[0].material["epsilon"] = value
        with pytest.raises(ProblemError, match="epsilon"):
            electrostatics.write_problem(scene, mesh, folder)
    assert not (folder / "problem.json").exists()


@pytest.mark.parametrize("bad", [5, 2.5])
def test_numbers_where_expressions_are_expected_are_a_finding(tmp_path, electrostatics, bad):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    scene.boundaries[0].condition.values["g"] = bad
    with pytest.raises(ProblemError, match="g must be an expression string"):
        electrostatics.write_problem(scene, mesh, folder)
    scene.boundaries[0].condition.values["g"] = "5"
    scene.source["rho"] = bad
    with pytest.raises(ProblemError, match="rho must be an expression string"):
        electrostatics.write_problem(scene, mesh, folder)


def test_mesh_with_a_region_the_scene_lacks_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    scene.regions = scene.regions[:1]
    with pytest.raises(ProblemError, match="the mesh has a region 'air' the scene does not"):
        electrostatics.write_problem(scene, mesh, folder)


def test_mesh_with_a_boundary_the_scene_lacks_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    scene.boundaries.append(Boundary("interface", Between("glass", "air")))
    mesh, folder = make_run(tmp_path, scene)
    scene.boundaries.pop()
    with pytest.raises(ProblemError, match="the mesh has a boundary 'interface'"):
        electrostatics.write_problem(scene, mesh, folder)


@pytest.mark.parametrize(
    "kwargs", [{"tolerance": -1.0}, {"tolerance": float("nan")}, {"max_iterations": 0}]
)
def test_solver_settings_are_checked_when_built(kwargs):
    with pytest.raises(ProblemError):
        SolverSettings(**kwargs)


def test_unsupported_solver_method_is_refused(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    with pytest.raises(ProblemError, match="method 'lu'"):
        electrostatics.write_problem(scene, mesh, folder, SolverSettings(method="lu"))


def test_the_file_is_strict_json(tmp_path, electrostatics):
    scene = capacitor_scene()
    mesh, folder = make_run(tmp_path, scene)
    path = electrostatics.write_problem(scene, mesh, folder)
    assert not re.search(r"\b(NaN|Infinity)\b", path.read_text())
