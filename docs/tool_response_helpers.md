# Tool Response Helper Functions

## Overview

The `agent_skills.adapters.tool_response` module provides helper functions for building `ToolResponse` objects. These functions standardize the creation of tool responses across all tool operations (list, activate, read, run, search) and provide consistent error handling.

## Purpose

These helper functions serve several important purposes:

1. **Consistency**: Ensure all tool responses follow the unified format specified in Requirement 5.6
2. **Convenience**: Simplify the creation of ToolResponse objects with sensible defaults
3. **Error Handling**: Provide a standard way to convert exceptions to error responses
4. **Maintainability**: Centralize response building logic for easier updates

## Available Functions

### Success Response Builders

#### `build_metadata_response(skill_name, descriptors, meta=None)`

Builds a response for the `skills.list` tool.

**Parameters:**
- `skill_name` (str): Name of the skill or "all" for list operations
- `descriptors` (list[SkillDescriptor]): List of skill descriptors
- `meta` (dict, optional): Additional metadata

**Returns:** ToolResponse with type="metadata"

**Example:**
```python
from agent_skills import build_metadata_response, SkillDescriptor
from pathlib import Path

skills = [
    SkillDescriptor(
        name="data-processor",
        description="Process data files",
        path=Path("/skills/data-processor"),
    )
]

response = build_metadata_response("all", skills)
```

#### `build_instructions_response(skill_name, instructions, skill_path, meta=None)`

Builds a response for the `skills.activate` tool.

**Parameters:**
- `skill_name` (str): Name of the skill
- `instructions` (str): The SKILL.md body content
- `skill_path` (str): Path to SKILL.md file
- `meta` (dict, optional): Additional metadata

**Returns:** ToolResponse with type="instructions"

**Features:**
- Automatically calculates content bytes and SHA256 hash
- Handles Unicode content correctly

**Example:**
```python
response = build_instructions_response(
    skill_name="data-processor",
    instructions="# Data Processor\n\nProcess CSV files...",
    skill_path="SKILL.md",
)
```

#### `build_reference_response(skill_name, reference_path, content, truncated=False, meta=None)`

Builds a response for reading a reference file.

**Parameters:**
- `skill_name` (str): Name of the skill
- `reference_path` (str): Relative path to the reference file
- `content` (str): The file content
- `truncated` (bool): Whether the content was truncated
- `meta` (dict, optional): Additional metadata

**Returns:** ToolResponse with type="reference"

**Example:**
```python
response = build_reference_response(
    skill_name="data-processor",
    reference_path="references/api-docs.md",
    content="# API Documentation...",
    truncated=False,
)
```

#### `build_asset_response(skill_name, asset_path, content, truncated=False, meta=None)`

Builds a response for reading an asset file (binary).

**Parameters:**
- `skill_name` (str): Name of the skill
- `asset_path` (str): Relative path to the asset file
- `content` (bytes): The binary file content
- `truncated` (bool): Whether the content was truncated
- `meta` (dict, optional): Additional metadata

**Returns:** ToolResponse with type="asset"

**Example:**
```python
response = build_asset_response(
    skill_name="data-processor",
    asset_path="assets/diagram.png",
    content=b"\x89PNG\r\n...",
    truncated=False,
)
```

#### `build_execution_response(skill_name, script_path, result, meta=None)`

Builds a response for script execution.

**Parameters:**
- `skill_name` (str): Name of the skill
- `script_path` (str): Relative path to the executed script
- `result` (ExecutionResult): ExecutionResult object
- `meta` (dict, optional): Additional metadata (merged with result.meta)

**Returns:** ToolResponse with type="execution_result"

**Example:**
```python
from agent_skills import ExecutionResult

result = ExecutionResult(
    exit_code=0,
    stdout="Processing complete\n",
    stderr="",
    duration_ms=1234,
    meta={"sandbox": "local_subprocess"},
)

response = build_execution_response(
    skill_name="data-processor",
    script_path="scripts/process.py",
    result=result,
)
```

#### `build_search_response(skill_name, query, results, meta=None)`

Builds a response for full-text search.

**Parameters:**
- `skill_name` (str): Name of the skill
- `query` (str): The search query string
- `results` (list[dict]): List of search result dictionaries
- `meta` (dict, optional): Additional metadata

**Returns:** ToolResponse with type="search_results"

**Features:**
- Automatically adds query and result_count to meta

**Example:**
```python
results = [
    {
        "path": "references/api-docs.md",
        "line_num": 42,
        "context": "...authentication token...",
    }
]

response = build_search_response(
    skill_name="data-processor",
    query="authentication",
    results=results,
)
```

### Error Response Builder

#### `build_error_response(skill_name, error, path=None, include_traceback=False)`

Builds an error response from an exception.

**Parameters:**
- `skill_name` (str): Name of the skill
- `error` (Exception): The exception that occurred
- `path` (str, optional): Path related to the error
- `include_traceback` (bool): Whether to include full traceback in meta

**Returns:** ToolResponse with ok=False and type="error"

**Features:**
- Automatically extracts error type and message
- Includes error details in meta
- Optionally includes full traceback for debugging

**Example:**
```python
from agent_skills import SkillNotFoundError

try:
    # Some operation that fails
    raise SkillNotFoundError("Skill 'test' not found")
except Exception as e:
    response = build_error_response(
        skill_name="test",
        error=e,
        include_traceback=True,
    )
```

### Utility Function

#### `safe_tool_call(skill_name, operation, path=None, include_traceback=False)`

Executes a tool operation and converts any exceptions to error responses.

**Parameters:**
- `skill_name` (str): Name of the skill
- `operation` (callable): Callable that returns a ToolResponse
- `path` (str, optional): Path related to the operation
- `include_traceback` (bool): Whether to include full traceback in error responses

**Returns:** ToolResponse (either success from operation or error response)

**Example:**
```python
def do_work():
    # This might raise an exception
    return build_instructions_response("my-skill", "content", "SKILL.md")

# Automatically catches and converts exceptions
response = safe_tool_call("my-skill", do_work)

# Response will be either:
# - Success response from do_work()
# - Error response if do_work() raised an exception
```

## Usage in Adapters

These helper functions are designed to be used in the LangChain and ADK adapters:

### LangChain Example

```python
from agent_skills.adapters.tool_response import (
    build_instructions_response,
    build_error_response,
)
from langchain.tools import BaseTool

class SkillsActivateTool(BaseTool):
    name = "skills.activate"
    description = "Load and return skill instructions"
    
    def _run(self, name: str) -> str:
        try:
            handle = self.repository.open(name)
            instructions = handle.instructions()
            
            response = build_instructions_response(
                skill_name=name,
                instructions=instructions,
                skill_path="SKILL.md",
            )
            
            return response.to_dict()
        except Exception as e:
            response = build_error_response(name, e)
            return response.to_dict()
```

### ADK Example

```python
from agent_skills.adapters.tool_response import safe_tool_call

def handle_activate(repository, params):
    """Handler for skills.activate tool."""
    skill_name = params["name"]
    
    def operation():
        handle = repository.open(skill_name)
        instructions = handle.instructions()
        return build_instructions_response(
            skill_name=skill_name,
            instructions=instructions,
            skill_path="SKILL.md",
        )
    
    # Automatically handles errors
    response = safe_tool_call(skill_name, operation)
    return response.to_dict()
```

## Response Format

All helper functions produce ToolResponse objects with the following structure:

```python
@dataclass
class ToolResponse:
    ok: bool                          # True for success, False for error
    type: str                         # Response type (metadata, instructions, etc.)
    skill: str                        # Skill name
    path: str | None                  # File path (if applicable)
    content: str | bytes | dict | None  # Response content
    bytes: int | None                 # Content size in bytes
    sha256: str | None                # SHA256 hash of content
    truncated: bool                   # Whether content was truncated
    meta: dict                        # Additional metadata
```

### Success Response Example

```json
{
  "ok": true,
  "type": "instructions",
  "skill": "data-processor",
  "path": "SKILL.md",
  "content": "# Data Processor\n\n...",
  "bytes": 1234,
  "sha256": "abc123...",
  "truncated": false,
  "meta": {}
}
```

### Error Response Example

```json
{
  "ok": false,
  "type": "error",
  "skill": "data-processor",
  "path": "../../etc/passwd",
  "content": "PathTraversalError: Path contains '..' component",
  "bytes": null,
  "sha256": null,
  "truncated": false,
  "meta": {
    "error_type": "PathTraversalError",
    "error_details": {...}
  }
}
```

## Testing

Comprehensive unit tests are provided in `tests/adapters/test_tool_response.py`:

- 35 test cases covering all helper functions
- Tests for success responses with various content types
- Tests for error responses with different exception types
- Tests for serialization and JSON compatibility
- Tests for the safe_tool_call wrapper

Run tests with:
```bash
pytest tests/adapters/test_tool_response.py -v
```

## Design Rationale

### Why Helper Functions?

1. **DRY Principle**: Avoid repeating response construction logic across multiple tools
2. **Type Safety**: Ensure all responses have the correct structure
3. **Hash Calculation**: Automatically compute SHA256 hashes for content integrity
4. **Error Standardization**: Consistent error response format across all tools
5. **Future Proofing**: Easy to update response format in one place

### Why safe_tool_call?

The `safe_tool_call` wrapper provides:

1. **Automatic Error Handling**: No need to write try/except in every tool
2. **Consistent Error Responses**: All exceptions converted to standard format
3. **Debugging Support**: Optional traceback inclusion for development
4. **Cleaner Code**: Tool implementations focus on business logic, not error handling

## Requirements Validation

This implementation satisfies **Requirement 5.6**:

> FOR ALL tool responses, THE Agent_Skills_Runtime SHALL return a unified JSON structure with fields: ok, type, skill, path, content, bytes, sha256, truncated, meta

All helper functions produce ToolResponse objects with these exact fields, ensuring consistency across all tool operations.

## Future Enhancements

Potential improvements for future versions:

1. **Response Validation**: Add schema validation for response content
2. **Compression**: Support for compressed content in responses
3. **Streaming**: Support for streaming large responses
4. **Caching**: Built-in response caching based on SHA256
5. **Metrics**: Automatic metrics collection for response sizes and types
