"""Helper functions for building ToolResponse objects.

This module provides convenience functions for creating ToolResponse objects
for different tool operations (list, activate, read, run, search) and for
converting exceptions to error responses.
"""

import hashlib
import traceback
from typing import Any

from agent_skills.exceptions import AgentSkillsError
from agent_skills.models import ExecutionResult, SkillDescriptor, ToolResponse


def build_metadata_response(
    skill_name: str,
    descriptors: list[SkillDescriptor],
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for skills.list tool.

    Args:
        skill_name: Name of the skill (or "all" for list operations)
        descriptors: List of SkillDescriptor objects
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="metadata"
    """
    content = [desc.to_dict() for desc in descriptors]

    return ToolResponse(
        ok=True,
        type="metadata",
        skill=skill_name,
        path=None,
        content=content,
        bytes=None,
        sha256=None,
        truncated=False,
        meta=meta or {},
    )


def build_instructions_response(
    skill_name: str,
    instructions: str,
    skill_path: str,
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for skills.activate tool.

    Args:
        skill_name: Name of the skill
        instructions: The SKILL.md body content
        skill_path: Path to SKILL.md file
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="instructions"
    """
    content_bytes = instructions.encode("utf-8")
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()

    return ToolResponse(
        ok=True,
        type="instructions",
        skill=skill_name,
        path=skill_path,
        content=instructions,
        bytes=len(content_bytes),
        sha256=sha256_hash,
        truncated=False,
        meta=meta or {},
    )


def build_reference_response(
    skill_name: str,
    reference_path: str,
    content: str,
    truncated: bool = False,
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for reading a reference file.

    Args:
        skill_name: Name of the skill
        reference_path: Relative path to the reference file
        content: The file content
        truncated: Whether the content was truncated
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="reference"
    """
    content_bytes = content.encode("utf-8")
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()

    return ToolResponse(
        ok=True,
        type="reference",
        skill=skill_name,
        path=reference_path,
        content=content,
        bytes=len(content_bytes),
        sha256=sha256_hash,
        truncated=truncated,
        meta=meta or {},
    )


def build_asset_response(
    skill_name: str,
    asset_path: str,
    content: bytes,
    truncated: bool = False,
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for reading an asset file.

    Args:
        skill_name: Name of the skill
        asset_path: Relative path to the asset file
        content: The binary file content
        truncated: Whether the content was truncated
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="asset"
    """
    sha256_hash = hashlib.sha256(content).hexdigest()

    return ToolResponse(
        ok=True,
        type="asset",
        skill=skill_name,
        path=asset_path,
        content=content,
        bytes=len(content),
        sha256=sha256_hash,
        truncated=truncated,
        meta=meta or {},
    )


def build_execution_response(
    skill_name: str,
    script_path: str,
    result: ExecutionResult,
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for script execution.

    Args:
        skill_name: Name of the skill
        script_path: Relative path to the executed script
        result: ExecutionResult object
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="execution_result"
    """
    # Merge result.meta with provided meta
    merged_meta = {**result.meta, **(meta or {})}

    return ToolResponse(
        ok=True,
        type="execution_result",
        skill=skill_name,
        path=script_path,
        content=result.to_dict(),
        bytes=None,
        sha256=None,
        truncated=False,
        meta=merged_meta,
    )


def build_search_response(
    skill_name: str,
    query: str,
    results: list[dict],
    meta: dict | None = None,
) -> ToolResponse:
    """Build a success response for full-text search.

    Args:
        skill_name: Name of the skill
        query: The search query string
        results: List of search result dictionaries
        meta: Optional metadata dictionary

    Returns:
        ToolResponse with type="search_results"
    """
    merged_meta = {
        "query": query,
        "result_count": len(results),
        **(meta or {}),
    }

    return ToolResponse(
        ok=True,
        type="search_results",
        skill=skill_name,
        path=None,
        content=results,
        bytes=None,
        sha256=None,
        truncated=False,
        meta=merged_meta,
    )


def build_error_response(
    skill_name: str,
    error: Exception,
    path: str | None = None,
    include_traceback: bool = False,
) -> ToolResponse:
    """Build an error response from an exception.

    Args:
        skill_name: Name of the skill
        error: The exception that occurred
        path: Optional path related to the error
        include_traceback: Whether to include full traceback in meta

    Returns:
        ToolResponse with ok=False and type="error"
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Build error content string
    content = f"{error_type}: {error_message}"

    # Build meta with error details
    meta: dict[str, Any] = {
        "error_type": error_type,
    }

    # Add additional details for specific error types
    if hasattr(error, "__dict__"):
        error_details = {
            k: v for k, v in error.__dict__.items()
            if not k.startswith("_") and k not in ("args",)
        }
        if error_details:
            meta["error_details"] = error_details

    # Include traceback if requested
    if include_traceback:
        meta["traceback"] = traceback.format_exc()

    return ToolResponse(
        ok=False,
        type="error",
        skill=skill_name,
        path=path,
        content=content,
        bytes=None,
        sha256=None,
        truncated=False,
        meta=meta,
    )


def safe_tool_call(
    skill_name: str,
    operation: callable,
    path: str | None = None,
    include_traceback: bool = False,
) -> ToolResponse:
    """Execute a tool operation and convert any exceptions to error responses.

    This is a convenience wrapper that catches all exceptions and converts them
    to properly formatted error responses.

    Args:
        skill_name: Name of the skill
        operation: Callable that returns a ToolResponse
        path: Optional path related to the operation
        include_traceback: Whether to include full traceback in error responses

    Returns:
        ToolResponse (either success from operation or error response)

    Example:
        >>> def do_work():
        ...     return build_instructions_response("my-skill", "content", "SKILL.md")
        >>> response = safe_tool_call("my-skill", do_work)
    """
    try:
        return operation()
    except Exception as e:
        return build_error_response(
            skill_name=skill_name,
            error=e,
            path=path,
            include_traceback=include_traceback,
        )
