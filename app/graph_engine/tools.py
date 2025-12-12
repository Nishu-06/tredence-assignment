"""Tool registry for managing callable Python tools"""

from typing import Dict, Callable, Any, Optional
import inspect
import uuid


class ToolRegistry:
    """Registry for managing and executing tools"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_descriptions: Dict[str, str] = {}
    
    def register(self, name: str, func: Callable, description: Optional[str] = None):
        """
        Register a tool in the registry.
        
        Args:
            name: Name of the tool
            func: Callable function that takes state as input
            description: Optional description of what the tool does
        """
        if not callable(func):
            raise ValueError(f"Tool '{name}' must be callable")
        
        # Check if function signature accepts state
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        
        if len(params) == 0:
            raise ValueError(f"Tool '{name}' must accept at least one parameter (state)")
        
        self._tools[name] = func
        self._tool_descriptions[name] = description or f"Tool: {name}"
    
    def get(self, name: str) -> Optional[Callable]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def execute(self, name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given state.
        
        Args:
            name: Name of the tool to execute
            state: Current workflow state dictionary
            
        Returns:
            Updated state dictionary
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        
        tool = self._tools[name]
        
        # Execute the tool with state
        result = tool(state)
        
        # If result is a dict, merge it into state
        if isinstance(result, dict):
            state.update(result)
            return state
        
        # If result is not a dict, wrap it
        return state
    
    def list_tools(self) -> Dict[str, str]:
        """List all registered tools with their descriptions"""
        return self._tool_descriptions.copy()
    
    def unregister(self, name: str):
        """Unregister a tool from the registry"""
        if name in self._tools:
            del self._tools[name]
            del self._tool_descriptions[name]
    
    def exists(self, name: str) -> bool:
        """Check if a tool exists in the registry"""
        return name in self._tools


# Global tool registry instance
tool_registry = ToolRegistry()


# Example tool: detect_smells
def detect_smells(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detects code smells in the provided code.
    
    Args:
        state: Workflow state containing 'code' key
        
    Returns:
        Dictionary with 'smell_count' and 'smells' keys
    """
    code = state.get("code", "")
    
    # Mock implementation: count potential issues
    smells = []
    smell_count = 0
    
    # Simple heuristics for code smells
    if len(code.split("\n")) > 50:
        smells.append("Long function detected")
        smell_count += 1
    
    if code.count("if") + code.count("elif") > 5:
        smells.append("High cyclomatic complexity")
        smell_count += 1
    
    if "pass" in code and "def" in code:
        smells.append("Empty function detected")
        smell_count += 1
    
    return {
        "smell_count": smell_count,
        "smells": smells
    }


# Register default tools
tool_registry.register("detect_smells", detect_smells, "Detects code smells in source code")

