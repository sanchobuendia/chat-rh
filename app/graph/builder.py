from app.graph.state import ChatState
from langgraph.graph import START, END, StateGraph


def build_graph(router_node, rag_node, payroll_node, smalltalk_node, finalize_node):
    graph = StateGraph(ChatState)
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("payroll", payroll_node)
    graph.add_node("smalltalk", smalltalk_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "router")

    def branch(state: ChatState):
        return state.get("route", "rag")

    graph.add_conditional_edges(
        "router",
        branch,
        {
            "rag": "rag",
            "payroll": "payroll",
            "smalltalk": "smalltalk",
        },
    )
    graph.add_edge("rag", "finalize")
    graph.add_edge("payroll", "finalize")
    graph.add_edge("smalltalk", "finalize")
    graph.add_edge("finalize", END)
    return graph
