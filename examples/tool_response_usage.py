"""Example usage of tool response helper functions.

This demonstrates how to use the helper functions to build ToolResponse
objects for different tool operations.
"""

from pathlib import Path

from agent_skills.adapters.tool_response import (
    build_asset_response,
    build_error_response,
    build_execution_response,
    build_instructions_response,
    build_metadata_response,
    build_reference_response,
    build_search_response,
    safe_tool_call,
)
from agent_skills.exceptions import SkillNotFoundError
from agent_skills.models import ExecutionResult, SkillDescriptor


def example_list_skills():
    """Example: Building a metadata response for skills.list tool."""
    # Simulate discovered skills
    skills = [
        SkillDescriptor(
            name="data-processor",
            description="Process CSV and JSON data files",
            path=Path("/skills/data-processor"),
            hash="abc123",
            mtime=1234567890.0,
        ),
        SkillDescriptor(
            name="api-client",
            description="Make HTTP API calls with authentication",
            path=Path("/skills/api-client"),
            hash="def456",
            mtime=1234567891.0,
        ),
    ]
    
    # Build response
    response = build_metadata_response("all", skills)
    
    print("List Skills Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Skills: {len(response.content)}")
    for skill in response.content:
        print(f"    - {skill['name']}: {skill['description']}")
    print()


def example_activate_skill():
    """Example: Building an instructions response for skills.activate tool."""
    instructions = """# Data Processor Skill

This skill processes CSV and JSON data files.

## Usage

1. Read the API documentation from references/
2. Execute the setup script
3. Process your data files

## Examples

See references/examples.md for detailed examples.
"""
    
    # Build response
    response = build_instructions_response(
        skill_name="data-processor",
        instructions=instructions,
        skill_path="SKILL.md",
        meta={"cached": False},
    )
    
    print("Activate Skill Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Skill: {response.skill}")
    print(f"  Bytes: {response.bytes}")
    print(f"  SHA256: {response.sha256[:16]}...")
    print(f"  Content preview: {response.content[:50]}...")
    print()


def example_read_reference():
    """Example: Building a reference response for skills.read tool."""
    api_docs = """# API Documentation

## Authentication

Use Bearer token authentication:

```
Authorization: Bearer <token>
```

## Endpoints

- GET /data - List all data files
- POST /data - Upload new data file
"""
    
    # Build response
    response = build_reference_response(
        skill_name="data-processor",
        reference_path="references/api-docs.md",
        content=api_docs,
        truncated=False,
    )
    
    print("Read Reference Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Path: {response.path}")
    print(f"  Bytes: {response.bytes}")
    print(f"  Truncated: {response.truncated}")
    print()


def example_read_asset():
    """Example: Building an asset response for binary files."""
    # Simulate binary data (e.g., PNG image header)
    binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    
    # Build response
    response = build_asset_response(
        skill_name="data-processor",
        asset_path="assets/diagram.png",
        content=binary_data,
        truncated=False,
    )
    
    print("Read Asset Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Path: {response.path}")
    print(f"  Bytes: {response.bytes}")
    print(f"  Content type: {type(response.content)}")
    print()


def example_run_script():
    """Example: Building an execution response for skills.run tool."""
    # Simulate script execution result
    result = ExecutionResult(
        exit_code=0,
        stdout="Processing complete\nProcessed 1000 records\n",
        stderr="",
        duration_ms=1234,
        meta={"sandbox": "local_subprocess"},
    )
    
    # Build response
    response = build_execution_response(
        skill_name="data-processor",
        script_path="scripts/process.py",
        result=result,
        meta={"args": ["--input", "data.csv"]},
    )
    
    print("Run Script Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Path: {response.path}")
    print(f"  Exit Code: {response.content['exit_code']}")
    print(f"  Duration: {response.content['duration_ms']}ms")
    print(f"  Output: {response.content['stdout'].strip()}")
    print()


def example_search():
    """Example: Building a search response for skills.search tool."""
    # Simulate search results
    results = [
        {
            "path": "references/api-docs.md",
            "line_num": 5,
            "context": "Use Bearer token authentication:",
        },
        {
            "path": "references/examples.md",
            "line_num": 12,
            "context": "Example with authentication token:",
        },
    ]
    
    # Build response
    response = build_search_response(
        skill_name="data-processor",
        query="authentication",
        results=results,
    )
    
    print("Search Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Query: {response.meta['query']}")
    print(f"  Results: {response.meta['result_count']}")
    for result in response.content:
        print(f"    - {result['path']}:{result['line_num']}")
    print()


def example_error_handling():
    """Example: Building error responses."""
    # Simulate an error
    error = SkillNotFoundError("Skill 'nonexistent-skill' not found")
    
    # Build error response
    response = build_error_response(
        skill_name="nonexistent-skill",
        error=error,
        path=None,
        include_traceback=False,
    )
    
    print("Error Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Error Type: {response.meta['error_type']}")
    print(f"  Message: {response.content}")
    print()


def example_safe_tool_call():
    """Example: Using safe_tool_call wrapper."""
    
    def risky_operation():
        """Simulate an operation that might fail."""
        # This would normally do real work
        raise SkillNotFoundError("Skill not found")
    
    # Wrap the operation with safe_tool_call
    response = safe_tool_call(
        skill_name="test-skill",
        operation=risky_operation,
        include_traceback=False,
    )
    
    print("Safe Tool Call Response:")
    print(f"  OK: {response.ok}")
    print(f"  Type: {response.type}")
    print(f"  Error caught and converted: {not response.ok}")
    print()


def example_json_serialization():
    """Example: Serializing responses to JSON."""
    import json
    
    # Build a response
    response = build_instructions_response(
        skill_name="test-skill",
        instructions="# Test Skill\n\nThis is a test.",
        skill_path="SKILL.md",
    )
    
    # Convert to dict (JSON-compatible)
    response_dict = response.to_dict()
    
    # Serialize to JSON string
    json_str = json.dumps(response_dict, indent=2)
    
    print("JSON Serialization:")
    print(json_str[:200] + "...")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Tool Response Helper Functions - Usage Examples")
    print("=" * 60)
    print()
    
    example_list_skills()
    example_activate_skill()
    example_read_reference()
    example_read_asset()
    example_run_script()
    example_search()
    example_error_handling()
    example_safe_tool_call()
    example_json_serialization()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
