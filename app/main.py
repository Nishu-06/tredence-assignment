"""FastAPI application entrypoint"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
import asyncio

from app.graph_engine.engine import workflow_engine, Graph, Node
from app.graph_engine.state import WorkflowState, ExecutionLogEntry
from app.graph_engine.tools import tool_registry
from app.database import db
from app.workflows import code_review  # Import to register workflow functions


app = FastAPI(
    title="Mini Agent Workflow Engine",
    description="A FastAPI-based mini agent workflow engine similar to LangGraph",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models for Request/Response Validation

class NodeDefinition(BaseModel):
    """Definition of a workflow node"""
    function: str = Field(..., description="Name of the function to execute")
    type: str = Field(default="function", description="Type of the node")


class CreateGraphRequest(BaseModel):
    """Request model for creating a graph"""
    name: str = Field(..., description="Name of the graph")
    nodes: Dict[str, NodeDefinition] = Field(..., description="Dictionary of node definitions")
    edges: Dict[str, str] = Field(..., description="Dictionary mapping from_node -> to_node")
    entry_node: str = Field(..., description="Starting node name")


class CreateGraphResponse(BaseModel):
    """Response model for graph creation"""
    graph_id: str = Field(..., description="Unique identifier for the created graph")
    message: str = Field(..., description="Success message")


class RunWorkflowRequest(BaseModel):
    """Request model for running a workflow"""
    graph_id: str = Field(..., description="ID of the graph to execute")
    initial_state: Dict[str, Any] = Field(..., description="Initial state dictionary")


class RunWorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    run_id: str = Field(..., description="Unique identifier for the workflow run")
    final_state: Dict[str, Any] = Field(..., description="Final state after execution")
    execution_log: List[Dict[str, Any]] = Field(..., description="Execution log entries")


class WorkflowStateResponse(BaseModel):
    """Response model for workflow state"""
    run_id: str = Field(..., description="Unique identifier for the workflow run")
    current_state: Dict[str, Any] = Field(..., description="Current state dictionary")
    execution_log: List[Dict[str, Any]] = Field(..., description="Execution log entries")
    status: str = Field(..., description="Status of the workflow (running, completed, failed, stopped)")
    current_node: Optional[str] = Field(None, description="Current node being executed")


class RegisterToolRequest(BaseModel):
    """Request model for registering a tool"""
    name: str = Field(..., description="Name of the tool")
    description: Optional[str] = Field(None, description="Description of the tool")


class RegisterToolResponse(BaseModel):
    """Response model for tool registration"""
    message: str = Field(..., description="Success message")
    tool_name: str = Field(..., description="Name of the registered tool")


class GraphInfo(BaseModel):
    """Information about a graph"""
    graph_id: str
    name: str
    node_count: int
    edge_count: int
    created_at: str


class RunInfo(BaseModel):
    """Information about a workflow run"""
    run_id: str
    graph_id: str
    status: str
    created_at: str
    updated_at: str
    log_entry_count: int


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Mini Agent Workflow Engine API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/graph/create", response_model=CreateGraphResponse)
async def create_graph(request: CreateGraphRequest):
    """
    Create a new workflow graph.
    
    Args:
        request: Graph creation request with nodes, edges, and entry node
        
    Returns:
        Graph ID and success message
    """
    try:
        # Convert node definitions to the format expected by engine
        nodes_dict = {
            name: {
                "function": node_def.function,
                "type": node_def.type
            }
            for name, node_def in request.nodes.items()
        }
        
        graph_id = workflow_engine.create_graph(
            name=request.name,
            nodes=nodes_dict,
            edges=request.edges,
            entry_node=request.entry_node
        )
        
        # Save to database
        graph = workflow_engine.get_graph(graph_id)
        if graph:
            db.save_graph(graph)
        
        return CreateGraphResponse(
            graph_id=graph_id,
            message="Graph created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/graph/run", response_model=RunWorkflowResponse)
async def run_workflow(request: RunWorkflowRequest):
    """
    Execute a workflow graph.
    
    Args:
        request: Workflow execution request with graph_id and initial state
        
    Returns:
        Run ID, final state, and execution log
    """
    try:
        # Define loop condition: continue looping if quality_score < threshold
        def loop_condition(state: Dict[str, Any]) -> bool:
            quality_score = state.get("quality_score", 0)
            threshold = state.get("threshold", 80)
            return quality_score < threshold
        
        run_id = workflow_engine.run_workflow(
            graph_id=request.graph_id,
            initial_state=request.initial_state,
            loop_condition=loop_condition
        )
        
        # Get the run state
        run_state = workflow_engine.get_run_state(run_id)
        if not run_state:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Save to database
        db.save_run(run_state)
        
        # Convert execution log to dict format
        execution_log = [
            {
                "node": entry.node,
                "timestamp": entry.timestamp,
                "state_snapshot": entry.state_snapshot,
                "message": entry.message
            }
            for entry in run_state.execution_log
        ]
        
        return RunWorkflowResponse(
            run_id=run_id,
            final_state=run_state.state,
            execution_log=execution_log
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/graph/state/{run_id}", response_model=WorkflowStateResponse)
async def get_workflow_state(run_id: str):
    """
    Get the current state of a workflow run.
    
    Args:
        run_id: Unique identifier for the workflow run
        
    Returns:
        Current state, execution log, and status
    """
    run_state = workflow_engine.get_run_state(run_id)
    if not run_state:
        # Try to get from database
        run_state = db.get_run(run_id)
        if not run_state:
            raise HTTPException(status_code=404, detail="Run not found")
    
    # Convert execution log to dict format
    execution_log = [
        {
            "node": entry.node,
            "timestamp": entry.timestamp,
            "state_snapshot": entry.state_snapshot,
            "message": entry.message
        }
        for entry in run_state.execution_log
    ]
    
    return WorkflowStateResponse(
        run_id=run_state.run_id,
        current_state=run_state.state,
        execution_log=execution_log,
        status=run_state.status,
        current_node=run_state.current_node
    )


@app.get("/graph/list", response_model=List[GraphInfo])
async def list_graphs():
    """List all created graphs"""
    graphs = db.list_graphs()
    return [
        GraphInfo(
            graph_id=graph["graph_id"],
            name=graph["name"],
            node_count=graph["node_count"],
            edge_count=graph["edge_count"],
            created_at=graph["created_at"]
        )
        for graph in graphs
    ]


@app.get("/graph/{graph_id}")
async def get_graph(graph_id: str):
    """Get information about a specific graph"""
    graph = workflow_engine.get_graph(graph_id)
    if not graph:
        graph = db.get_graph(graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
    
    return {
        "graph_id": graph.graph_id,
        "name": graph.name,
        "nodes": {name: {"function": node.function, "type": node.node_type} 
                 for name, node in graph.nodes.items()},
        "edges": graph.edges,
        "entry_node": graph.entry_node
    }


@app.get("/runs/list", response_model=List[RunInfo])
async def list_runs(graph_id: Optional[str] = None):
    """List all workflow runs, optionally filtered by graph_id"""
    runs = db.list_runs(graph_id=graph_id)
    return [
        RunInfo(
            run_id=run["run_id"],
            graph_id=run["graph_id"],
            status=run["status"],
            created_at=run["created_at"],
            updated_at=run["updated_at"],
            log_entry_count=run["log_entry_count"]
        )
        for run in runs
    ]


@app.post("/tools/register", response_model=RegisterToolResponse)
async def register_tool(request: RegisterToolRequest):
    """
    Register a new tool in the tool registry.
    
    Note: This endpoint currently only registers tool metadata.
    For actual tool functions, they should be registered programmatically.
    
    Args:
        request: Tool registration request with name and description
        
    Returns:
        Success message and tool name
    """
    # In a real implementation, you might want to accept the function code
    # or a reference to a function. For now, we'll just validate the name.
    if tool_registry.exists(request.name):
        raise HTTPException(
            status_code=400,
            detail=f"Tool '{request.name}' already exists"
        )
    
    # Note: Actual function registration would require the function code
    # This is a simplified version that just validates the request
    return RegisterToolResponse(
        message="Tool registration endpoint. Use programmatic registration for actual functions.",
        tool_name=request.name
    )


@app.get("/tools/list")
async def list_tools():
    """List all registered tools"""
    tools = tool_registry.list_tools()
    return {
        "tools": [
            {"name": name, "description": desc}
            for name, desc in tools.items()
        ],
        "count": len(tools)
    }


@app.websocket("/graph/run/{graph_id}/stream")
async def stream_workflow_execution(websocket: WebSocket, graph_id: str):
    """
    WebSocket endpoint for streaming workflow execution logs in real-time.
    
    Args:
        websocket: WebSocket connection
        graph_id: ID of the graph to execute
    """
    await websocket.accept()
    
    try:
        # Receive initial state from client
        data = await websocket.receive_text()
        initial_state = json.loads(data)
        
        # Create a custom execution handler that sends logs via WebSocket
        # This is a simplified version - in a full implementation,
        # you'd modify the engine to support callbacks
        
        # For now, we'll run the workflow and stream the final result
        def loop_condition(state: Dict[str, Any]) -> bool:
            quality_score = state.get("quality_score", 0)
            threshold = state.get("threshold", 80)
            return quality_score < threshold
        
        run_id = workflow_engine.run_workflow(
            graph_id=graph_id,
            initial_state=initial_state,
            loop_condition=loop_condition
        )
        
        run_state = workflow_engine.get_run_state(run_id)
        
        # Stream execution log entries
        for entry in run_state.execution_log:
            await websocket.send_json({
                "type": "log_entry",
                "node": entry.node,
                "timestamp": entry.timestamp,
                "state_snapshot": entry.state_snapshot,
                "message": entry.message
            })
            await asyncio.sleep(0.1)  # Small delay for streaming effect
        
        # Send final result
        await websocket.send_json({
            "type": "completed",
            "run_id": run_id,
            "final_state": run_state.state,
            "status": run_state.status
        })
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

