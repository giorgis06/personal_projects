import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.field import Field
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Rectangle
from femstudio.physics import registry

EPSILON_0 = 8.8541878128e-12


@pytest.fixture
def setup():
    nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]], dtype=float)
    mesh = MeshData(
        nodes=nodes,
        node_tags=np.arange(1, 6),
        triangles=np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]),
        edges=np.empty((0, 2), dtype=int),
        regions={"glass": np.array([0, 1]), "air": np.array([2, 3])},
        boundaries={},
    )
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    scene = Scene(
        "electrostatics",
        [square],
        [
            Region("glass", square, {"epsilon": 4.0}),
            Region("air", square, {"epsilon": ((1.0, 0.0), (0.0, 1.0))}),
        ],
    )
    u = Field("u", 3.0 * nodes[:, 0] + 2.0 * nodes[:, 1], "V")
    return scene, mesh, u


def test_field_is_minus_the_gradient(setup):
    scene, mesh, u = setup
    fields = registry.get("electrostatics").derive(scene, mesh, u)
    np.testing.assert_allclose(fields["E"].values, np.tile([-3.0, -2.0], (4, 1)), atol=1e-12)
    assert fields["E"].location == "triangle" and fields["E"].unit == "V/m"
    assert fields["E"].is_vector


def test_magnitude(setup):
    scene, mesh, u = setup
    fields = registry.get("electrostatics").derive(scene, mesh, u)
    np.testing.assert_allclose(fields["E_magnitude"].values, 13**0.5)


def test_energy_density_uses_epsilon_0_and_the_regions_permittivity(setup):
    scene, mesh, u = setup
    density = registry.get("electrostatics").derive(scene, mesh, u)["energy_density"]
    glass, air = 0.5 * EPSILON_0 * 4.0 * 13.0, 0.5 * EPSILON_0 * 1.0 * 13.0
    np.testing.assert_allclose(density.values, [glass, glass, air, air], rtol=1e-12)
    assert density.unit == "J/m^3"


def test_derived_names_are_the_declared_derived_outputs(setup):
    scene, mesh, u = setup
    problem = registry.get("electrostatics")
    declared = {o.name for o in problem.output_fields if o.derived}
    assert set(problem.derive(scene, mesh, u)) == declared
