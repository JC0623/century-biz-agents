from .market import MarketTool
from .realestate import RealEstateTool
from .industry import IndustryTool
from .valuation import ValuationTool
from .macro import MacroTool
from .ip import IPTool
from agents.state import ToolName

MCP_CLIENTS: dict[ToolName, object] = {
    "tool_market": MarketTool(),
    "tool_realestate": RealEstateTool(),
    "tool_industry": IndustryTool(),
    "tool_valuation": ValuationTool(),
    "tool_macro": MacroTool(),
    "tool_ip": IPTool(),
}
