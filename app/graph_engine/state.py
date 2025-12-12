"""State management for workflow execution"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class ExecutionLogEntry(BaseModel):
    """Represents a single entry in the execution log"""
    node: str
    timestamp: str
    state_snapshot: Dict[str, Any]
    message: Optional[str] = None


class WorkflowState(BaseModel):
    """Represents the state of a workflow execution"""
    state: Dict[str, Any]
    execution_log: list[ExecutionLogEntry]
    current_node: Optional[str] = None
    status: str = "running"  # running, completed, failed, stopped
    run_id: str
    graph_id: str
    created_at: str
    updated_at: str

    def add_log_entry(self, node: str, state_snapshot: Dict[str, Any], message: Optional[str] = None):
        """Add an entry to the execution log"""
        entry = ExecutionLogEntry(
            node=node,
            timestamp=datetime.utcnow().isoformat(),
            state_snapshot=state_snapshot.copy(),
            message=message
        )
        self.execution_log.append(entry)
        self.updated_at = datetime.utcnow().isoformat()

    def update_state(self, updates: Dict[str, Any]):
        """Update the state dictionary with new values"""
        self.state.update(updates)
        self.updated_at = datetime.utcnow().isoformat()

    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the state dictionary"""
        return self.state.get(key, default)

    def set_status(self, status: str):
        """Set the workflow status"""
        self.status = status
        self.updated_at = datetime.utcnow().isoformat()

