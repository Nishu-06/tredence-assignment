"""
Example usage script for the Mini Agent Workflow Engine

This script demonstrates how to use the API to create and run workflows.
Run this after starting the FastAPI server with: uvicorn app.main:app --reload
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2))


def main():
    print("Mini Agent Workflow Engine - Example Usage")
    print("=" * 60)
    
    # Step 1: Create a graph
    print("\n1. Creating workflow graph...")
    graph_response = requests.post(
        f"{BASE_URL}/graph/create",
        json={
            "name": "code_review",
            "nodes": {
                "extract_functions": {
                    "function": "extract_functions",
                    "type": "function"
                },
                "check_complexity": {
                    "function": "check_complexity",
                    "type": "function"
                },
                "detect_issues": {
                    "function": "detect_issues",
                    "type": "function"
                },
                "suggest_improvements": {
                    "function": "suggest_improvements",
                    "type": "function"
                }
            },
            "edges": {
                "extract_functions": "check_complexity",
                "check_complexity": "detect_issues",
                "detect_issues": "suggest_improvements",
                "suggest_improvements": "check_complexity"  # Loop back
            },
            "entry_node": "extract_functions"
        }
    )
    
    if graph_response.status_code != 200:
        print(f"Error creating graph: {graph_response.text}")
        return
    
    graph_data = graph_response.json()
    graph_id = graph_data["graph_id"]
    print_response("Graph Created", graph_data)
    
    # Step 2: Run the workflow
    print("\n2. Running workflow...")
    run_response = requests.post(
        f"{BASE_URL}/graph/run",
        json={
            "graph_id": graph_id,
            "initial_state": {
                "code": """
def complex_function(x, y, z, a, b, c):
    if x > 0:
        if y > 0:
            if z > 0:
                if a > 0:
                    if b > 0:
                        if c > 0:
                            return x + y + z + a + b + c
    return 0

def simple_function():
    pass

def another_function(param1, param2, param3, param4, param5, param6, param7):
    result = param1 + param2
    return result
""",
                "quality_score": 0,
                "threshold": 80
            }
        }
    )
    
    if run_response.status_code != 200:
        print(f"Error running workflow: {run_response.text}")
        return
    
    run_data = run_response.json()
    run_id = run_data["run_id"]
    print_response("Workflow Execution Result", {
        "run_id": run_id,
        "final_quality_score": run_data["final_state"].get("quality_score"),
        "nodes_visited": len(run_data["execution_log"]),
        "status": "See full response below"
    })
    
    # Step 3: Get workflow state
    print("\n3. Getting workflow state...")
    state_response = requests.get(f"{BASE_URL}/graph/state/{run_id}")
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print_response("Workflow State", {
            "run_id": state_data["run_id"],
            "status": state_data["status"],
            "quality_score": state_data["current_state"].get("quality_score"),
            "issue_count": state_data["current_state"].get("issue_count"),
            "suggestion_count": state_data["current_state"].get("suggestion_count"),
            "execution_log_entries": len(state_data["execution_log"])
        })
    
    # Step 4: List all tools
    print("\n4. Listing registered tools...")
    tools_response = requests.get(f"{BASE_URL}/tools/list")
    
    if tools_response.status_code == 200:
        tools_data = tools_response.json()
        print_response("Registered Tools", tools_data)
    
    # Step 5: List all graphs
    print("\n5. Listing all graphs...")
    graphs_response = requests.get(f"{BASE_URL}/graph/list")
    
    if graphs_response.status_code == 200:
        graphs_data = graphs_response.json()
        print_response("All Graphs", graphs_data)
    
    print("\n" + "=" * 60)
    print("Example usage completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API server.")
        print("Please make sure the server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\nError: {e}")

