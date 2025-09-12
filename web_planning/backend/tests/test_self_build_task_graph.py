from web_planning.backend.self_build.task_graph import (
    to_dag,
    infer_dependencies,
    topological_order,
    topological_layers,
    critical_path,
)


def sample_tasks():
    return [
        {
            "id": "core-logic",
            "title": "Implement core logic [P1]",
            "impact": 0.9,
            "effort": 0.6,
            "priority": "P1",
            "source": "X",
            "line": 1,
            "tags": [],
            "path_hint": "web_planning/backend/self_build/core.py",
        },
        {
            "id": "tests-core",
            "title": "Add unit tests for core logic [P2]",
            "impact": 0.7,
            "effort": 0.5,
            "priority": "P2",
            "source": "X",
            "line": 2,
            "tags": [],
            "path_hint": "tests/backend/self_build/test_core.py",
        },
        {
            "id": "docs-core",
            "title": "Write docs for core logic [P3]",
            "impact": 0.55,
            "effort": 0.45,
            "priority": "P3",
            "source": "X",
            "line": 3,
            "tags": [],
            "path_hint": "docs/self_build/core.md",
        },
        {
            "id": "refactor-core",
            "title": "Refactor core for clarity [P2]",
            "impact": 0.7,
            "effort": 0.5,
            "priority": "P2",
            "source": "X",
            "line": 4,
            "tags": [],
            "path_hint": "web_planning/backend/self_build/core.py",
        },
    ]


def test_infer_dependencies_cluster_and_kinds():
    tasks = sample_tasks()
    deps = infer_dependencies(tasks)
    # tests/docs depend on code/refactor in same cluster
    assert "core-logic" not in deps["core-logic"]
    assert "core-logic" in deps["tests-core"]
    assert "refactor-core" in deps["tests-core"]
    assert "core-logic" in deps["docs-core"]


def test_to_dag_layers_and_order():
    dag = to_dag(sample_tasks())
    # Kind annotations exist
    kinds = {n["id"]: n["kind"] for n in dag}
    assert kinds["tests-core"] == "test"
    assert kinds["docs-core"] == "doc"

    # Layering respects deps
    layers = topological_layers(dag)
    flat = [tid for layer in layers for tid in layer]
    assert flat.index("core-logic") < flat.index("tests-core")
    assert flat.index("refactor-core") < flat.index("tests-core")

    order = topological_order(dag)
    assert order.index("core-logic") < order.index("tests-core")


def test_critical_path_by_effort():
    dag = to_dag(sample_tasks())
    total, path = critical_path(dag, weight_key="effort")
    # One possible longest path passes through core-logic -> tests-core
    assert total >= 1.0
    assert path[0] in {"core-logic", "refactor-core"}
