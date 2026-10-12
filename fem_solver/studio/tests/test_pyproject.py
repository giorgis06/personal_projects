def test_markers_are_registered_and_strict(pytestconfig):
    names = {line.split(":")[0].strip() for line in pytestconfig.getini("markers")}
    assert {"ui", "real_solver"} <= names
    assert pytestconfig.getoption("strict_markers")
