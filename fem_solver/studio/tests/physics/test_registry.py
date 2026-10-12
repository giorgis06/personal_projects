import pytest
from femstudio.physics import registry
from femstudio.physics.base import ProblemType
from femstudio.physics.electrostatics.spec import Electrostatics


class Dummy(ProblemType):
    name = "dummy_heat"
    label = "Heat"
    material_fields = ()
    boundary_kinds = ()
    source_fields = ()
    output_fields = ()

    def write_problem(self, scene, mesh, folder, settings=None):
        raise NotImplementedError


@pytest.fixture
def clean_registry(monkeypatch):
    monkeypatch.setattr(registry, "_registered", dict(registry._registered))
    return registry


def test_electrostatics_is_found_without_being_imported_by_the_caller():
    assert isinstance(registry.get("electrostatics"), Electrostatics)
    assert "electrostatics" in [p.name for p in registry.available()]


def test_unknown_name_lists_what_is_registered():
    with pytest.raises(registry.UnknownProblemType, match="registered: .*electrostatics"):
        registry.get("magnetostatics")


def test_a_new_problem_type_is_registered_not_special_cased(clean_registry):
    clean_registry.register(Dummy())
    assert clean_registry.get("dummy_heat").label == "Heat"
    assert [p.name for p in clean_registry.available()] == ["dummy_heat", "electrostatics"]


def test_registering_a_name_twice_is_refused(clean_registry):
    clean_registry.register(Dummy())
    with pytest.raises(ValueError, match="already registered"):
        clean_registry.register(Dummy())
