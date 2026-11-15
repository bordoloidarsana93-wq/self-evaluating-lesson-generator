"""LangGraph wiring: which step runs after which. This is the only file that uses LangGraph.

    plan -> generate -> [inject_error, only with --inject-error] -> evaluate
    evaluate -> finalize            (all checks pass, or no retries left)
    evaluate -> revise -> evaluate  (some checks fail and retries remain)
    finalize -> reflect -> END

The nodes are plain functions in `nodes.py`. `partial` hands each one the shared
`services` object, because LangGraph itself only passes the state.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from . import nodes
from .services import Services
from .state import LessonState


def build_graph(services: Services):
    """Build and compile the workflow graph."""
    graph = StateGraph(LessonState)

    graph.add_node("plan", partial(nodes.plan, services=services))
    graph.add_node("generate", partial(nodes.generate, services=services))
    graph.add_node("inject_error", partial(nodes.inject_error, services=services))
    graph.add_node("evaluate", partial(nodes.evaluate, services=services))
    graph.add_node("revise", partial(nodes.revise, services=services))
    graph.add_node("finalize", partial(nodes.finalize, services=services))
    graph.add_node("reflect", partial(nodes.reflect, services=services))

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "generate")
    graph.add_conditional_edges("generate", nodes.route_after_generate, ["inject_error", "evaluate"])
    graph.add_edge("inject_error", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        partial(nodes.route_after_evaluate, max_retries=services.settings.max_retries),
        ["revise", "finalize"],
    )
    graph.add_edge("revise", "evaluate")
    graph.add_edge("finalize", "reflect")
    graph.add_edge("reflect", END)

    return graph.compile()
