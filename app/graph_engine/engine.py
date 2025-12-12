"""Core workflow engine for executing graphs"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid

from .state import WorkflowState, ExecutionLogEntry
from .tools import tool_registry


class Node:
    """Represents a node in the workflow graph"""
    
    def __init__(self, name: str, function: str, node_type: str = "function", 
                 condition: Optional[Callable] = None):
        self.name = name
        self.function = function
        self.node_type = node_type
        self.condition = condition  # Optional condition function for conditional execution
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the node function.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state dictionary
        """
        if self.node_type == "function":
            # Get the function from tool registry or workflow functions
            func = tool_registry.get(self.function)
            if func:
                return func(state)
            else:
                raise ValueError(f"Function '{self.function}' not found")
        else:
            # For other node types, return state as-is
            return state


class Edge:
    """Represents an edge in the workflow graph"""
    
    def __init__(self, from_node: str, to_node: str, condition: Optional[Callable] = None):
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition  # Optional condition function for conditional branching
    
    def should_traverse(self, state: Dict[str, Any]) -> bool:
        """
        Check if this edge should be traversed based on the current state.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if edge should be traversed, False otherwise
        """
        if self.condition is None:
            return True
        return self.condition(state)


class Graph:
    """Represents a workflow graph"""
    
    def __init__(self, graph_id: str, name: str, nodes: Dict[str, Node], 
                 edges: Dict[str, str], entry_node: str):
        self.graph_id = graph_id
        self.name = name
        self.nodes = nodes
        self.edges = edges  # Maps from_node -> to_node
        self.entry_node = entry_node
    
    def get_next_node(self, current_node: str, state: Dict[str, Any]) -> Optional[str]:
        """
        Get the next node to execute based on edges and conditions.
        
        Args:
            current_node: Current node name
            state: Current workflow state
            
        Returns:
            Next node name or None if no next node
        """
        if current_node not in self.edges:
            return None
        
        next_node_name = self.edges[current_node]
        
        # Check if edge has a condition
        edge = Edge(current_node, next_node_name)
        if edge.should_traverse(state):
            return next_node_name
        
        return None
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the graph structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.entry_node:
            return False, "Entry node is required"
        
        if self.entry_node not in self.nodes:
            return False, f"Entry node '{self.entry_node}' not found in nodes"
        
        # Check that all edges reference valid nodes
        for from_node, to_node in self.edges.items():
            if from_node not in self.nodes:
                return False, f"Edge from '{from_node}' references non-existent node"
            if to_node not in self.nodes:
                return False, f"Edge to '{to_node}' references non-existent node"
        
        return True, None


class WorkflowEngine:
    """Core engine for executing workflow graphs"""
    
    def __init__(self):
        self.graphs: Dict[str, Graph] = {}
        self.runs: Dict[str, WorkflowState] = {}
        self.max_iterations = 1000  # Prevent infinite loops
        self.max_loop_iterations = 10  # Max iterations for a single loop
    
    def create_graph(self, name: str, nodes: Dict[str, Dict[str, Any]], 
                    edges: Dict[str, str], entry_node: str) -> str:
        """
        Create a new workflow graph.
        
        Args:
            name: Name of the graph
            nodes: Dictionary of node definitions
            edges: Dictionary mapping from_node -> to_node
            entry_node: Starting node name
            
        Returns:
            Graph ID
        """
        graph_id = str(uuid.uuid4())
        
        # Convert node definitions to Node objects
        node_objects = {}
        for node_name, node_def in nodes.items():
            node_objects[node_name] = Node(
                name=node_name,
                function=node_def.get("function", node_name),
                node_type=node_def.get("type", "function")
            )
        
        graph = Graph(graph_id, name, node_objects, edges, entry_node)
        
        # Validate graph
        is_valid, error = graph.validate()
        if not is_valid:
            raise ValueError(f"Invalid graph: {error}")
        
        self.graphs[graph_id] = graph
        return graph_id
    
    def run_workflow(self, graph_id: str, initial_state: Dict[str, Any], 
                    loop_condition: Optional[Callable] = None) -> str:
        """
        Execute a workflow graph.
        
        Args:
            graph_id: ID of the graph to execute
            initial_state: Initial state dictionary
            loop_condition: Optional function that returns True to continue looping
            
        Returns:
            Run ID
        """
        if graph_id not in self.graphs:
            raise ValueError(f"Graph '{graph_id}' not found")
        
        graph = self.graphs[graph_id]
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create workflow state
        workflow_state = WorkflowState(
            state=initial_state.copy(),
            execution_log=[],
            current_node=None,
            status="running",
            run_id=run_id,
            graph_id=graph_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        self.runs[run_id] = workflow_state
        
        try:
            current_node_name = graph.entry_node
            visited_nodes = set()
            iteration_count = 0
            loop_iteration_count = 0
            last_node_in_loop = None
            
            while current_node_name and iteration_count < self.max_iterations:
                iteration_count += 1
                
                # Check for infinite loops
                if current_node_name in visited_nodes:
                    loop_iteration_count += 1
                    if loop_iteration_count > self.max_loop_iterations:
                        workflow_state.add_log_entry(
                            current_node_name,
                            workflow_state.state.copy(),
                            "Loop iteration limit reached"
                        )
                        workflow_state.set_status("stopped")
                        break
                else:
                    loop_iteration_count = 0
                    visited_nodes.add(current_node_name)
                
                # Execute current node
                node = graph.nodes[current_node_name]
                workflow_state.current_node = current_node_name
                
                try:
                    # Execute node function
                    updated_state = node.execute(workflow_state.state)
                    workflow_state.update_state(updated_state)
                    
                    # Log execution
                    workflow_state.add_log_entry(
                        current_node_name,
                        workflow_state.state.copy(),
                        f"Node '{current_node_name}' executed successfully"
                    )
                    
                except Exception as e:
                    workflow_state.add_log_entry(
                        current_node_name,
                        workflow_state.state.copy(),
                        f"Error in node '{current_node_name}': {str(e)}"
                    )
                    workflow_state.set_status("failed")
                    break
                
                # Check loop condition if provided
                if loop_condition:
                    if not loop_condition(workflow_state.state):
                        # Loop condition not met, continue to next node
                        pass
                    else:
                        # Loop condition met, check if we should continue looping
                        # This is handled by the edge traversal logic
                        pass
                
                # Get next node
                next_node = graph.get_next_node(current_node_name, workflow_state.state)
                
                # If no next node, check for loop condition
                if next_node is None:
                    # Check if we should loop based on state conditions
                    # For example, if quality_score < threshold, loop back
                    if loop_condition and loop_condition(workflow_state.state):
                        # Find a node to loop back to (e.g., check_complexity)
                        # This is a simplified approach - in practice, you'd have explicit loop edges
                        if "quality_score" in workflow_state.state:
                            quality_score = workflow_state.state.get("quality_score", 0)
                            threshold = workflow_state.state.get("threshold", 80)
                            if quality_score < threshold:
                                # Loop back to check_complexity if it exists
                                if "check_complexity" in graph.nodes:
                                    next_node = "check_complexity"
                                    loop_iteration_count += 1
                                    if loop_iteration_count > self.max_loop_iterations:
                                        workflow_state.set_status("stopped")
                                        break
                
                current_node_name = next_node
            
            if workflow_state.status == "running":
                workflow_state.set_status("completed")
            
            if iteration_count >= self.max_iterations:
                workflow_state.set_status("stopped")
                workflow_state.add_log_entry(
                    workflow_state.current_node or "unknown",
                    workflow_state.state.copy(),
                    "Maximum iterations reached"
                )
        
        except Exception as e:
            workflow_state.set_status("failed")
            workflow_state.add_log_entry(
                workflow_state.current_node or "unknown",
                workflow_state.state.copy(),
                f"Workflow execution failed: {str(e)}"
            )
        
        return run_id
    
    def get_run_state(self, run_id: str) -> Optional[WorkflowState]:
        """Get the state of a workflow run"""
        return self.runs.get(run_id)
    
    def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Get a graph by ID"""
        return self.graphs.get(graph_id)


# Global workflow engine instance
workflow_engine = WorkflowEngine()

