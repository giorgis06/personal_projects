import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.project.project import Project, ProjectError


def test_create_writes_the_scene_and_open_reads_it_back(tmp_path):
    scene = capacitor_scene()
    Project.create(tmp_path / "proj", scene)
    assert (tmp_path / "proj" / "scene.json").is_file()
    assert Project.open(tmp_path / "proj").load_scene() == scene


def test_create_will_not_overwrite_a_project(tmp_path):
    Project.create(tmp_path, capacitor_scene())
    with pytest.raises(ProjectError, match="already holds a project"):
        Project.create(tmp_path, capacitor_scene())


def test_open_needs_a_scene_file(tmp_path):
    with pytest.raises(ProjectError, match="holds no scene.json"):
        Project.open(tmp_path)


def test_saving_a_changed_scene(tmp_path):
    project = Project.create(tmp_path, capacitor_scene())
    scene = project.load_scene()
    scene.regions[0].material["epsilon"] = ((9.0, 0.0), (0.0, 9.0))
    project.save_scene(scene)
    assert Project.open(tmp_path).load_scene().regions[0].material["epsilon"][0][0] == 9.0


def test_runs_are_numbered_from_one(tmp_path):
    project = Project.create(tmp_path, capacitor_scene())
    assert project.runs() == []
    first, second = project.new_run(), project.new_run()
    assert (first.number, second.number) == (1, 2)
    assert first.folder.name == "run_001" and first.folder.is_dir()
    assert [run.number for run in project.runs()] == [1, 2]
    assert project.run(2).folder == second.folder


def test_numbers_continue_after_the_highest_and_sort_numerically(tmp_path):
    project = Project.create(tmp_path, capacitor_scene())
    for number in (2, 10, 9):
        (tmp_path / "runs" / f"run_{number:03d}").mkdir(parents=True)
    assert [run.number for run in project.runs()] == [2, 9, 10]
    assert project.new_run().number == 11


def test_unknown_run(tmp_path):
    project = Project.create(tmp_path, capacitor_scene())
    with pytest.raises(ProjectError, match="no run 4"):
        project.run(4)


def test_a_new_run_has_state_created(tmp_path):
    project = Project.create(tmp_path, capacitor_scene())
    assert project.new_run().state == "created"
