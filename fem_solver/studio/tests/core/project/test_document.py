from pathlib import Path

import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.project.document import (
    DocumentError,
    default_mesh_size,
    document_from_scene,
    open_document,
)
from femstudio.core.project.project import Project, ProjectError
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import SceneFileError, save_scene

DATA = Path(__file__).resolve().parents[3] / ".." / "tests" / "data"
EXAMPLE = Path(__file__).resolve().parents[3] / "examples" / "capacitor.scene.json"


def test_default_size_puts_forty_elements_across_the_longest_side():
    # the capacitor's wall has radius 2, so the scene is 4 across
    assert default_mesh_size(capacitor_scene()) == pytest.approx(4.0 / 40)


def test_a_scene_file_opens_meshed_with_its_names(tmp_path):
    document = open_document(EXAMPLE, tmp_path)
    assert document.scene == capacitor_scene()
    assert document.project is None
    assert document.region_names == ["glass", "air"]
    assert document.boundary_names == ["inner_electrode", "outer_wall"]
    assert set(document.mesh.regions) == {"glass", "air"}
    assert document.size == pytest.approx(0.1)
    assert (tmp_path / "mesh.msh").is_file()


def test_a_project_folder_opens_with_its_project(tmp_path):
    project = Project.create(tmp_path / "proj", capacitor_scene())
    document = open_document(tmp_path / "proj", tmp_path)
    assert document.project is not None and document.project.folder == project.folder
    assert document.scene == capacitor_scene()


def test_a_geo_file_opens_as_a_mesh_without_a_scene(tmp_path):
    document = open_document(DATA / "two_materials.geo", tmp_path)
    assert document.scene is None and document.project is None
    assert set(document.region_names) == {"glass", "air"}
    assert set(document.boundary_names) == {"outer", "interface"}
    assert document.size is None


def test_a_msh_file_opens_as_a_mesh(tmp_path):
    open_document(EXAMPLE, tmp_path)
    document = open_document(tmp_path / "mesh.msh", tmp_path)
    assert set(document.region_names) == {"glass", "air"}
    assert document.scene is None


def test_unknown_file_type(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("x")
    with pytest.raises(DocumentError, match="cannot open 'notes.txt'"):
        open_document(path, tmp_path)


def test_folder_that_is_not_a_project(tmp_path):
    with pytest.raises(ProjectError):
        open_document(tmp_path, tmp_path)


def test_broken_scene_file(tmp_path):
    path = tmp_path / "scene.json"
    path.write_text("{ nope")
    with pytest.raises(SceneFileError):
        open_document(path, tmp_path)


def test_an_empty_scene_opens_without_a_mesh(tmp_path):
    path = tmp_path / "empty.json"
    save_scene(Scene("electrostatics"), path)
    document = open_document(path, tmp_path)
    assert document.mesh is None
    assert "no shapes" in document.mesh_error
    assert document.scene == Scene("electrostatics")
    assert document.region_names == [] and document.boundary_names == []


def test_a_scene_with_unnamed_outer_edges_opens_and_says_why_it_has_no_mesh(tmp_path):
    scene = capacitor_scene()
    scene.boundaries.pop()
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    document = open_document(path, tmp_path)
    assert document.mesh is None
    assert "named by no boundary" in document.mesh_error
    assert document.region_names == ["glass", "air"]
    assert document.boundary_names == ["inner_electrode"]


def test_a_region_without_a_material_opens_with_the_validation_reason(tmp_path):
    scene = capacitor_scene()
    scene.regions[1].material = {}
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    document = open_document(path, tmp_path)
    assert document.mesh is None
    assert "region 'air'" in document.mesh_error and "no material" in document.mesh_error


def test_a_project_without_a_mesh_still_has_its_runs(tmp_path):
    scene = capacitor_scene()
    scene.regions[1].material = {}
    project = Project.create(tmp_path / "proj", scene)
    project.new_run()
    document = open_document(tmp_path / "proj", tmp_path)
    assert document.mesh is None and document.project is not None
    assert len(document.project.runs()) == 1


def test_the_default_boundary_is_listed_when_the_mesh_has_it(tmp_path):
    from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, BoundaryCondition

    scene = capacitor_scene()
    scene.boundaries.pop()
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    document = open_document(path, tmp_path)
    assert document.mesh is not None
    assert document.boundary_names == ["inner_electrode", DEFAULT_BOUNDARY_NAME]


def test_a_default_boundary_nobody_needs_is_not_listed(tmp_path):
    from femstudio.core.scene.boundary import BoundaryCondition

    scene = capacitor_scene()
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    assert open_document(path, tmp_path).boundary_names == ["inner_electrode", "outer_wall"]


def test_a_scene_is_meshed_at_the_size_asked_for(tmp_path):
    scene = capacitor_scene()
    size = default_mesh_size(scene) * 2
    document = document_from_scene(scene, Path("s.json"), tmp_path, size=size)
    assert document.size == size
    assert document.mesh is not None
    coarse = document.mesh.n_triangles
    fine = document_from_scene(scene, Path("s.json"), tmp_path)
    assert fine.size == default_mesh_size(scene)
    assert fine.mesh.n_triangles > coarse


@pytest.mark.parametrize("size", [0.0, -1.0, float("nan"), float("inf"), 1e-9])
def test_an_unusable_size_leaves_no_mesh_and_says_why(tmp_path, size):
    document = document_from_scene(capacitor_scene(), Path("s.json"), tmp_path, size=size)
    assert document.mesh is None
    assert document.scene is not None
    assert "element size" in document.mesh_error
