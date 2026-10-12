"""A stand-in for `fem` that honours the solver contract. FAKE_FEM_MODE selects its behaviour."""

import csv
import json
import math
import os
import sys
import time
from pathlib import Path

from femstudio.core.mesh.reader import read_mesh


def capacitor_potential(document: dict, nodes) -> list[float]:
    """The radial solution for the capacitor scene: radii 0.2, 0.5 and 2.0, flux continuous."""
    a, b, outer = 0.2, 0.5, 2.0
    eps_glass = document["regions"]["glass"]["epsilon"][0][0]
    eps_air = document["regions"]["air"]["epsilon"][0][0]
    volts = float(document["boundaries"]["inner_electrode"]["g"])
    charge = volts / (math.log(outer / b) / eps_air + math.log(b / a) / eps_glass)
    values = []
    for x, y in nodes:
        r = math.hypot(x, y)
        if r <= b:
            values.append(volts - charge / eps_glass * math.log(r / a))
        else:
            values.append(charge / eps_air * math.log(outer / r))
    return values


def main() -> int:
    mode = os.environ.get("FAKE_FEM_MODE", "ok")
    problem = Path(sys.argv[1])
    document = json.loads(problem.read_text())
    folder = problem.parent
    if mode == "slow":
        pid_file = folder / "pid.txt"
        pid_file.with_name("pid.tmp").write_text(str(os.getpid()))
        pid_file.with_name("pid.tmp").replace(pid_file)
    if mode == "binary_output":
        sys.stdout.buffer.write(b"progress \xff\xfe not utf-8\n")
        sys.stdout.buffer.flush()
    print(f"fake fem: problem {document['problem_type']}", flush=True)
    if mode == "slow":
        time.sleep(60)
    if mode == "chatty":
        for step in range(600):
            print(f"fake fem: step {step}", flush=True)
            time.sleep(0.05)

    if mode == "fail":
        print("matrix is singular: no dirichlet boundary", file=sys.stderr)
        return 3
    if mode == "silent_fail":
        return 4

    mesh = read_mesh(folder / document["mesh"])
    print(f"fake fem: {mesh.n_nodes} nodes", flush=True)
    result = folder / document["output"]
    result.mkdir(exist_ok=True)

    if mode != "missing_solution":
        if mode == "capacitor":
            values = capacitor_potential(document, mesh.nodes)
        else:
            values = [x + 2.0 * y for x, y in mesh.nodes]
        rows = list(zip(mesh.node_tags, values, strict=True))
        if mode == "shuffled":
            rows.reverse()
        with (result / "solution.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["node_tag", "u"])
            writer.writerows(rows)
    print("fake fem: cg iteration 7 residual 1e-11", flush=True)

    status = "failed" if mode == "failed_status" else "success"
    run = {
        "status": status,
        "iterations": 7,
        "residual": 1e-11,
        "timings": {"assemble": 0.01, "solve": 0.02},
        "message": "did not converge" if status == "failed" else "",
    }
    text = "{not json" if mode == "malformed_run" else json.dumps(run)
    (result / "run.json").write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
