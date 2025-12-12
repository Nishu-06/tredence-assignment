"""Database layer for persistence (in-memory implementation)"""

from typing import Dict, Optional, Any
from datetime import datetime
import json

from app.graph_engine.state import WorkflowState
from app.graph_engine.engine import Graph


class InMemoryDatabase:
    """In-memory database for storing graphs and runs"""
    
    def __init__(self):
        self.graphs: Dict[str, Graph] = {}
        self.runs: Dict[str, WorkflowState] = {}
        self.graph_metadata: Dict[str, Dict[str, Any]] = {}
        self.run_metadata: Dict[str, Dict[str, Any]] = {}
    
    def save_graph(self, graph: Graph, metadata: Optional[Dict[str, Any]] = None):
        """Save a graph to the database"""
        self.graphs[graph.graph_id] = graph
        self.graph_metadata[graph.graph_id] = {
            "name": graph.name,
            "created_at": datetime.utcnow().isoformat(),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            **(metadata or {})
        }
    
    def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Get a graph from the database"""
        return self.graphs.get(graph_id)
    
    def list_graphs(self) -> list[Dict[str, Any]]:
        """List all graphs with metadata"""
        return [
            {
                "graph_id": graph_id,
                **metadata
            }
            for graph_id, metadata in self.graph_metadata.items()
        ]
    
    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph from the database"""
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            if graph_id in self.graph_metadata:
                del self.graph_metadata[graph_id]
            return True
        return False
    
    def save_run(self, run_state: WorkflowState, metadata: Optional[Dict[str, Any]] = None):
        """Save a workflow run to the database"""
        self.runs[run_state.run_id] = run_state
        self.run_metadata[run_state.run_id] = {
            "graph_id": run_state.graph_id,
            "status": run_state.status,
            "created_at": run_state.created_at,
            "updated_at": run_state.updated_at,
            "log_entry_count": len(run_state.execution_log),
            **(metadata or {})
        }
    
    def get_run(self, run_id: str) -> Optional[WorkflowState]:
        """Get a workflow run from the database"""
        return self.runs.get(run_id)
    
    def list_runs(self, graph_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """List all runs, optionally filtered by graph_id"""
        runs = []
        for run_id, metadata in self.run_metadata.items():
            if graph_id is None or metadata.get("graph_id") == graph_id:
                runs.append({
                    "run_id": run_id,
                    **metadata
                })
        return runs
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a workflow run from the database"""
        if run_id in self.runs:
            del self.runs[run_id]
            if run_id in self.run_metadata:
                del self.run_metadata[run_id]
            return True
        return False


# Global database instance
db = InMemoryDatabase()

