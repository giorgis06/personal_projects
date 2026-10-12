from pathlib import Path

import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.mesh.mesher import MeshError
from femstudio.core.project.document import (
    DocumentError,
    default_mesh_size,
    open_document,
)
from femstudio.core.project.project import Project, ProjectError
from femstudio.core.scene.region import Region
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


def test_scene_that_cannot_be_meshed_raises_the_mesh_error(tmp_path):
    scene = Scene("electrostatics")
    path = tmp_path / "empty.json"
    save_scene(scene, path)
    with pytest.raises(DocumentError, match="no shapes"):
        open_document(path, tmp_path)


def test_scene_with_unnamed_outer_edges_is_refused(tmp_path):
    scene = capacitor_scene()
    scene.boundaries.pop()
    scene.regions[1] = Region("air", scene.regions[1].area, {"epsilon": 1.0})
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    with pytest.raises(MeshError, match="named by no boundary"):
        open_document(path, tmp_path)
