"""Code Review Mini-Agent workflow functions"""

from typing import Dict, Any
import re
import ast

from app.graph_engine.tools import tool_registry


def extract_functions(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract function definitions from code.
    
    Args:
        state: Workflow state containing 'code' key
        
    Returns:
        Dictionary with 'functions' key containing list of function info
    """
    code = state.get("code", "")
    functions = []
    
    try:
        # Parse the code as AST
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "line_number": node.lineno,
                    "args_count": len(node.args.args),
                    "has_docstring": ast.get_docstring(node) is not None,
                    "body_lines": len(node.body) if node.body else 0
                }
                functions.append(func_info)
    except SyntaxError:
        # If parsing fails, use simple regex fallback
        pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:'
        matches = re.finditer(pattern, code)
        for match in matches:
            functions.append({
                "name": match.group(1),
                "line_number": code[:match.start()].count('\n') + 1,
                "args_count": match.group(0).count(',') + 1 if ',' in match.group(0) else 0,
                "has_docstring": False,
                "body_lines": 0
            })
    
    return {
        "functions": functions,
        "function_count": len(functions)
    }


def check_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check code complexity metrics.
    
    Args:
        state: Workflow state containing 'code' and 'functions' keys
        
    Returns:
        Dictionary with complexity metrics
    """
    code = state.get("code", "")
    functions = state.get("functions", [])
    
    # Calculate complexity metrics
    total_lines = len(code.split("\n"))
    total_functions = len(functions)
    
    # Count control flow statements
    if_count = code.count(" if ")
    elif_count = code.count(" elif ")
    for_count = code.count(" for ")
    while_count = code.count(" while ")
    cyclomatic_complexity = 1 + if_count + elif_count + for_count + while_count
    
    # Calculate average function complexity
    avg_complexity = cyclomatic_complexity / max(total_functions, 1)
    
    # Determine complexity level
    if avg_complexity < 5:
        complexity_level = "low"
    elif avg_complexity < 10:
        complexity_level = "medium"
    else:
        complexity_level = "high"
    
    return {
        "complexity": {
            "cyclomatic_complexity": cyclomatic_complexity,
            "average_complexity": avg_complexity,
            "complexity_level": complexity_level,
            "total_lines": total_lines,
            "control_flow_statements": if_count + elif_count + for_count + while_count
        }
    }


def detect_issues(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect code quality issues.
    
    Args:
        state: Workflow state containing 'code', 'functions', and 'complexity' keys
        
    Returns:
        Dictionary with detected issues
    """
    code = state.get("code", "")
    functions = state.get("functions", [])
    complexity = state.get("complexity", {})
    
    issues = []
    issue_count = 0
    
    # Check for missing docstrings
    for func in functions:
        if not func.get("has_docstring", False):
            issues.append({
                "type": "missing_docstring",
                "severity": "low",
                "function": func.get("name"),
                "message": f"Function '{func.get('name')}' is missing a docstring"
            })
            issue_count += 1
    
    # Check for high complexity
    if complexity.get("complexity_level") == "high":
        issues.append({
            "type": "high_complexity",
            "severity": "medium",
            "message": f"High cyclomatic complexity detected: {complexity.get('cyclomatic_complexity')}"
        })
        issue_count += 1
    
    # Check for long functions
    for func in functions:
        if func.get("body_lines", 0) > 50:
            issues.append({
                "type": "long_function",
                "severity": "medium",
                "function": func.get("name"),
                "message": f"Function '{func.get('name')}' is too long ({func.get('body_lines')} lines)"
            })
            issue_count += 1
    
    # Check for too many arguments
    for func in functions:
        if func.get("args_count", 0) > 5:
            issues.append({
                "type": "too_many_arguments",
                "severity": "low",
                "function": func.get("name"),
                "message": f"Function '{func.get('name')}' has too many arguments ({func.get('args_count')})"
            })
            issue_count += 1
    
    # Check for empty functions
    for func in functions:
        if func.get("body_lines", 0) == 0:
            issues.append({
                "type": "empty_function",
                "severity": "low",
                "function": func.get("name"),
                "message": f"Function '{func.get('name')}' appears to be empty"
            })
            issue_count += 1
    
    return {
        "issues": issues,
        "issue_count": issue_count
    }


def suggest_improvements(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggest code improvements based on detected issues.
    
    Args:
        state: Workflow state containing 'code', 'functions', 'complexity', and 'issues' keys
        
    Returns:
        Dictionary with suggestions and updated quality_score
    """
    issues = state.get("issues", [])
    complexity = state.get("complexity", {})
    functions = state.get("functions", [])
    
    suggestions = []
    quality_score = 100  # Start with perfect score
    
    # Deduct points for each issue
    for issue in issues:
        severity = issue.get("severity", "low")
        if severity == "high":
            quality_score -= 10
        elif severity == "medium":
            quality_score -= 5
        else:
            quality_score -= 2
        
        # Generate suggestions based on issue type
        issue_type = issue.get("type")
        if issue_type == "missing_docstring":
            suggestions.append({
                "type": "add_docstring",
                "function": issue.get("function"),
                "suggestion": f"Add a docstring to function '{issue.get('function')}' describing its purpose, parameters, and return value"
            })
        elif issue_type == "high_complexity":
            suggestions.append({
                "type": "refactor_complexity",
                "suggestion": "Break down complex functions into smaller, more manageable functions"
            })
        elif issue_type == "long_function":
            suggestions.append({
                "type": "split_function",
                "function": issue.get("function"),
                "suggestion": f"Split function '{issue.get('function')}' into smaller functions"
            })
        elif issue_type == "too_many_arguments":
            suggestions.append({
                "type": "use_data_class",
                "function": issue.get("function"),
                "suggestion": f"Consider using a data class or dictionary for function '{issue.get('function')}' arguments"
            })
        elif issue_type == "empty_function":
            suggestions.append({
                "type": "implement_or_remove",
                "function": issue.get("function"),
                "suggestion": f"Either implement function '{issue.get('function')}' or remove it if not needed"
            })
    
    # Bonus points for good practices
    if all(func.get("has_docstring", False) for func in functions):
        quality_score += 5
    
    if complexity.get("complexity_level") == "low":
        quality_score += 5
    
    # Ensure quality score is within bounds
    quality_score = max(0, min(100, quality_score))
    
    return {
        "suggestions": suggestions,
        "quality_score": quality_score,
        "suggestion_count": len(suggestions)
    }


# Register workflow functions with tool registry
tool_registry.register("extract_functions", extract_functions, "Extract function definitions from code")
tool_registry.register("check_complexity", check_complexity, "Check code complexity metrics")
tool_registry.register("detect_issues", detect_issues, "Detect code quality issues")
tool_registry.register("suggest_improvements", suggest_improvements, "Suggest code improvements")

