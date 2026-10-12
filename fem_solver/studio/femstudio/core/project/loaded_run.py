from femstudio.core.project.run import Run
from femstudio.core.results.result_set import ResultSet
from femstudio.physics.base import ProblemType


def load_result_set(run: Run, problem_type: ProblemType) -> ResultSet:
    """Read a finished run and add the fields its problem type derives from the solution."""
    result = run.load_result(problem_type)
    derived = problem_type.derive(result.scene, result.mesh, result.solution)
    fields = {result.solution.name: result.solution}
    labels = {}
    for spec in problem_type.output_fields:
        if spec.derived and spec.name in derived:
            fields[spec.name] = derived[spec.name]
        labels[spec.name] = spec.label
    return ResultSet(run.number, result.mesh, fields, labels)
