from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from agents.state import OSIMASState, ToolName
from agents.nodes.planner import plan_tools
from agents.nodes.aggregator import aggregate_results, quality_gate
from agents.nodes.synthesizer import synthesize
from agents.nodes.fallback import fallback_search
from mcp_servers.registry import MCP_CLIENTS


async def call_mcp_tool(state: dict) -> dict:
    tool: ToolName = state["tool"]
    client = MCP_CLIENTS[tool]
    result = await client.call(
        region_id=state["region_id"],
        query=state["query"],
    )
    return {"tool_results": {tool: result}}


def route_tools(state: OSIMASState):
    return [
        Send("call_mcp_tool", {
            "tool": tool,
            "region_id": state["region_id"],
            "query": state["query"],
        })
        for tool in state["requested_tools"]
    ]


def build_graph() -> StateGraph:
    builder = StateGraph(OSIMASState)

    builder.add_node("plan_tools", plan_tools)
    builder.add_node("call_mcp_tool", call_mcp_tool)
    builder.add_node("aggregate_results", aggregate_results)
    builder.add_node("fallback_search", fallback_search)
    builder.add_node("synthesize", synthesize)

    builder.add_edge(START, "plan_tools")
    builder.add_conditional_edges("plan_tools", route_tools, ["call_mcp_tool"])
    builder.add_edge("call_mcp_tool", "aggregate_results")
    builder.add_conditional_edges(
        "aggregate_results",
        quality_gate,
        {"fallback": "fallback_search", "synthesize": "synthesize"},
    )
    builder.add_edge("fallback_search", "synthesize")
    builder.add_edge("synthesize", END)

    return builder.compile()


graph = build_graph()
