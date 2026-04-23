import os
from typing import TypedDict, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import json

# Load environment variables
load_dotenv()

# Define the state for the LangGraph workflow
class AgentState(TypedDict):
    """The state of the agent workflow."""
    report: Dict[str, Any]       # Raw diagnostic report from Phase 3
    augmented_context: Dict[str, Any]  # Additional context (Asset ID, Crew, etc.)
    summary: str                 # Final human-friendly summary
    error: Optional[str]         # Error message if any

# Define the Context Augmentation Node
def context_augmentation_node(state: AgentState) -> Dict[str, Any]:
    """
    Mocks a lookup to retrieve asset and crew information based on location estimates.
    In a real system, this would query a GIS or Asset Management database.
    """
    report = state["report"]
    location = report.get("location_est", "Unknown")
    fault_type = report.get("type", "Unknown")
    
    # Mock logic based on the diagnostic report
    # If location suggests Pole #42, it's near Transformer T-104
    asset_id = "Transformer T-104" if "Pole #42" in location else "Substation S-12"
    
    # Associate crews based on location or phase
    crew_id = "Crew #3" if "Phase A" in location else "Crew #7"  # nearest available
    
    # Estimate repair time based on fault type
    repair_estimates = {
        "Line-to-Ground Fault": "45 minutes",
        "Line-to-Line Fault": "1.5 hours",
        "High-Impedance Fault": "2 hours (complex signature)",
        "Normal": "0 minutes"
    }
    est_time = repair_estimates.get(fault_type, "Unknown")
    
    # Signature analysis (mocked)
    signature_notes = ""
    if "High-Impedance" in fault_type:
        signature_notes = "Signature suggests arcing due to vegetation contact."
    elif "Line-to-Ground" in fault_type:
        signature_notes = "Potential insulator failure or debris."

    return {
        "augmented_context": {
            "asset_id": asset_id,
            "primary_crew": crew_id,
            "repair_time_estimate": est_time,
            "signature_insight": signature_notes,
            "urgency": "High" if fault_type != "Normal" else "Low"
        }
    }

# Define the Field Agent Summarizer Node
def field_agent_summarizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Uses an LLM (Gemini) to translate technical data into a concise mobile alert.
    """
    report = state["report"]
    context = state["augmented_context"]
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        # Fallback to a rule-based template if no API key is present
        summary = (
            f"Alert: {report['type']} detected on {context['asset_id']}. "
            f"{context['signature_insight']} "
            f"Estimated repair time: {context['repair_time_estimate']}. "
            f"{context['primary_crew']} is the nearest available team."
        )
        return {"summary": summary}

    try:
        # Initialize the LLM
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert Power Grid Field Agent Dispatcher. "
                "Your goal is to translate technical ML diagnostic reports into clear, "
                "actionable summaries for field technicians on mobile devices. "
                "Keep it concise, professional, and highlight the most critical info: "
                "fault type, asset ID, estimated repair time, and crew assignment. "
                "If it's a High-Impedance fault, mention potential causes like vegetation arcing."
            )),
            ("human", (
                "Technical Report:\n"
                "- Fault Type: {type} (Confidence: {confidence:.0%})\n"
                "- Location: {location}\n"
                "- Timestamp: {timestamp}\n\n"
                "Field Context:\n"
                "- Asset: {asset_id}\n"
                "- Assigned Crew: {crew_id}\n"
                "- Est. Repair Time: {repair_time}\n"
                "- Signal Insights: {insight}\n\n"
                "Generate the mobile alert summary:"
            ))
        ])
        
        # Build the chain and invoke
        chain = prompt | model
        response = chain.invoke({
            "type": report["type"],
            "confidence": report["confidence"],
            "location": report["location_est"],
            "timestamp": report["timestamp"],
            "asset_id": context["asset_id"],
            "crew_id": context["primary_crew"],
            "repair_time": context["repair_time_estimate"],
            "insight": context["signature_insight"]
        })
        
        return {"summary": response.content.strip()}
        
    except Exception as e:
        return {
            "summary": "Agent error generating summary.",
            "error": str(e)
        }

# Build the LangGraph workflow
def create_field_agent_workflow():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("augment_context", context_augmentation_node)
    workflow.add_node("field_agent_summarizer", field_agent_summarizer_node)
    
    # Define edges: Start -> Augment -> Summarize -> End
    workflow.set_entry_point("augment_context")
    workflow.add_edge("augment_context", "field_agent_summarizer")
    workflow.add_edge("field_agent_summarizer", END)
    
    return workflow.compile()

# Singleton instance of the agent
agent_executor = create_field_agent_workflow()

class FieldAgent:
    """Interface for the Field Agent system."""
    
    @staticmethod
    def get_summary(diagnostic_report: Dict[str, Any]) -> str:
        """Process a diagnostic report and return a mobile-ready summary."""
        initial_state = {
            "report": diagnostic_report,
            "augmented_context": {},
            "summary": "",
            "error": None
        }
        
        result = agent_executor.invoke(initial_state)
        return result.get("summary", "Unable to generate summary.")

# ============== Query Agent Tools ==============

@tool
def get_grid_health_stats():
    """Returns general health statistics of the power grid, including uptime and fault frequency."""
    # This would normally import from main.py's data_store
    # For now, we'll return a structured summary
    return json.dumps({
        "uptime": "24.5 hours",
        "total_load": "450 MW",
        "active_faults": 0,
        "stability_index": "98.2%",
        "latest_event": "Normal operation"
    })

@tool
def get_sector_status(sector_id: str):
    """Returns the health status, load, and maintenance history of a specific sector."""
    sectors = {
        "Sector 5": {"status": "Critical", "issue": "Voltage sag detected near substation B", "load": "85%"},
        "Sector 1": {"status": "Healthy", "issue": "None", "load": "42%"},
        "Sector 12": {"status": "Maintenance", "issue": "Insulator replacement in progress", "load": "0%"}
    }
    return json.dumps(sectors.get(sector_id, {"status": "Unknown", "info": "No data for this sector ID"}))

@tool
def get_crew_assignments():
    """Returns current locations and status of all field crews."""
    return json.dumps([
        {"id": "Crew #3", "location": "Sector 5", "status": "Responding"},
        {"id": "Crew #1", "location": "Sector 2", "status": "Idle"},
        {"id": "Crew #7", "location": "Base", "status": "Standby"}
    ])

# ============== Query Agent Graph ==============

class QueryState(TypedDict):
    messages: List[Any]

def call_model(state: QueryState):
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    tools = [get_grid_health_stats, get_sector_status, get_crew_assignments]
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

tool_node = ToolNode([get_grid_health_stats, get_sector_status, get_crew_assignments])

def query_router(state: QueryState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

query_builder = StateGraph(QueryState)
query_builder.add_node("agent", call_model)
query_builder.add_node("tools", tool_node)
query_builder.set_entry_point("agent")
query_builder.add_conditional_edges("agent", query_router)
query_builder.add_edge("tools", "agent")
query_graph = query_builder.compile()

class GridConsultant:
    """Natural language interface for grid operations."""
    
    @staticmethod
    def ask(question: str) -> str:
        """Process a natural language query about the grid."""
        if not os.getenv("GOOGLE_API_KEY"):
            return "Query interface requires a GOOGLE_API_KEY to process natural language."
            
        inputs = {"messages": [("human", question)]}
        result = query_graph.invoke(inputs)
        return result["messages"][-1].content

# Demo usage
if __name__ == "__main__":
    mock_report = {
        "status": "FAULT",
        "type": "High-Impedance Fault",
        "confidence": 0.94,
        "location_est": "Phase A - Estimated Pole #42",
        "timestamp": datetime.now().isoformat()
    }
    
    print("--- [Field Agent Test] ---")
    print(f"Input Diagnostic: {mock_report['type']} ({mock_report['confidence']:.0%})")
    
    field_agent = FieldAgent()
    summary = field_agent.get_summary(mock_report)
    
    print(f"\nMobile Alert Result:\n{summary}")
    print("--------------------------")
