# AI Engineering Assignment - Mini Agent Workflow Engine

A FastAPI-based mini agent workflow engine similar to LangGraph, implementing a simplified workflow execution system with nodes, edges, conditional branching, and looping capabilities.

## Features

- **Core Workflow Engine**: Execute workflows with nodes, edges, conditional branching, and loops
- **Tool Registry**: Register and manage callable Python tools
- **RESTful API**: Create graphs, run workflows, and monitor execution state
- **Execution Logging**: Track visited nodes and state changes
- **Example Workflow**: Code Review Mini-Agent workflow included

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entrypoint
│   ├── database.py             # In-memory database for persistence
│   ├── graph_engine/
│   │   ├── __init__.py
│   │   ├── state.py            # State management
│   │   ├── engine.py           # Core workflow engine
│   │   └── tools.py            # Tool registry
│   └── workflows/
│       ├── __init__.py
│       └── code_review.py      # Example workflow
├── requirements.txt
└── README.md
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. Create a Graph
**POST** `/graph/create`

Creates a new workflow graph with nodes and edges.

**Request Body:**
```json
{
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
    "suggest_improvements": "check_complexity"
  },
  "entry_node": "extract_functions"
}
```

**Response:**
```json
{
  "graph_id": "abc123",
  "message": "Graph created successfully"
}
```

### 2. Run a Workflow
**POST** `/graph/run`

Executes a workflow graph with an initial state.

**Request Body:**
```json
{
  "graph_id": "abc123",
  "initial_state": {
    "code": "def example(): pass",
    "quality_score": 0,
    "threshold": 80
  }
}
```

**Response:**
```json
{
  "run_id": "run_xyz789",
  "final_state": {
    "code": "def example(): pass",
    "quality_score": 85,
    "threshold": 80,
    "functions": [...],
    "complexity": {...},
    "issues": [...],
    "suggestions": [...]
  },
  "execution_log": [
    {"node": "extract_functions", "timestamp": "...", "state_snapshot": {...}},
    {"node": "check_complexity", "timestamp": "...", "state_snapshot": {...}}
  ]
}
```

### 3. Get Workflow State
**GET** `/graph/state/{run_id}`

Retrieves the current state of a workflow run.

**Response:**
```json
{
  "run_id": "run_xyz789",
  "current_state": {...},
  "execution_log": [...],
  "status": "completed"
}
```

### 4. Register a Tool
**POST** `/tools/register`

Registers a new tool in the tool registry.

**Request Body:**
```json
{
  "name": "detect_smells",
  "description": "Detects code smells in source code"
}
```

**Response:**
```json
{
  "message": "Tool registered successfully",
  "tool_name": "detect_smells"
}
```

## Example Usage

### Step 1: Start the server
```bash
uvicorn app.main:app --reload
```

### Step 2: Create a graph
```bash
curl -X POST "http://localhost:8000/graph/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "code_review",
    "nodes": {
      "extract_functions": {"function": "extract_functions", "type": "function"},
      "check_complexity": {"function": "check_complexity", "type": "function"},
      "detect_issues": {"function": "detect_issues", "type": "function"},
      "suggest_improvements": {"function": "suggest_improvements", "type": "function"}
    },
    "edges": {
      "extract_functions": "check_complexity",
      "check_complexity": "detect_issues",
      "detect_issues": "suggest_improvements",
      "suggest_improvements": "check_complexity"
    },
    "entry_node": "extract_functions"
  }'
```

### Step 3: Run the workflow
```bash
curl -X POST "http://localhost:8000/graph/run" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "abc123",
    "initial_state": {
      "code": "def complex_function(x, y, z): return x + y + z",
      "quality_score": 0,
      "threshold": 80
    }
  }'
```

### Step 4: Check the state
```bash
curl "http://localhost:8000/graph/state/run_xyz789"
```

## Quick Start Example

You can use the provided `example_usage.py` script to test the API:

```bash
# In one terminal, start the server
uvicorn app.main:app --reload

# In another terminal, run the example
python example_usage.py
```

## Python Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a graph
graph_response = requests.post(
    f"{BASE_URL}/graph/create",
    json={
        "name": "code_review",
        "nodes": {
            "extract_functions": {"function": "extract_functions", "type": "function"},
            "check_complexity": {"function": "check_complexity", "type": "function"},
            "detect_issues": {"function": "detect_issues", "type": "function"},
            "suggest_improvements": {"function": "suggest_improvements", "type": "function"}
        },
        "edges": {
            "extract_functions": "check_complexity",
            "check_complexity": "detect_issues",
            "detect_issues": "suggest_improvements",
            "suggest_improvements": "check_complexity"
        },
        "entry_node": "extract_functions"
    }
)
graph_id = graph_response.json()["graph_id"]
print(f"Created graph: {graph_id}")

# Run the workflow
run_response = requests.post(
    f"{BASE_URL}/graph/run",
    json={
        "graph_id": graph_id,
        "initial_state": {
            "code": "def example(): pass",
            "quality_score": 0,
            "threshold": 80
        }
    }
)
result = run_response.json()
print(f"Run ID: {result['run_id']}")
print(f"Final Quality Score: {result['final_state']['quality_score']}")
print(f"Execution Log: {len(result['execution_log'])} nodes visited")
```

## Architecture

### Workflow Engine
The core engine (`app/graph_engine/engine.py`) handles:
- Node execution in sequence
- Edge traversal based on conditions
- Conditional branching (if state value > threshold)
- Looping until conditions are met
- Execution logging

### State Management
State is managed as a dictionary that can be modified by each node. The state is passed between nodes and logged at each step.

### Tool Registry
Tools are registered in a central registry and can be called by node functions. Tools are simple Python functions that take state as input and return modified state or results.

## Improvements & Future Enhancements

1. **Persistence**: Add SQLite/PostgreSQL database for graph and run persistence
2. **WebSocket Support**: Real-time log streaming during execution
3. **Error Handling**: Better error recovery and retry mechanisms
4. **Parallel Execution**: Support for parallel node execution
5. **Graph Validation**: Validate graph structure before execution
6. **Rate Limiting**: Add rate limiting for API endpoints
7. **Authentication**: Add JWT-based authentication
8. **Graph Visualization**: API endpoint to export graph structure for visualization
9. **Conditional Edges**: Support for complex conditional logic in edges
10. **State Versioning**: Track state changes with versioning

## License

MIT

