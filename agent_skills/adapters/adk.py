"""ADK adapter for Agent Skills Runtime.

This module provides ADK tool specifications and handlers for all skill operations:
- skills.list: List all available skills
- skills.activate: Load skill instructions with session management
- skills.read: Read references and assets with session management
- skills.run: Execute scripts with session management
- skills.search: Full-text search in references
- skills.check_file: Check if a file exists and get its properties
- skills.write_file: Write content to a file safely
- skills.delete_file: Delete a file with confirmation
- skills.list_files: List files and directories in tree structure

All tools return unified JSON responses using the ToolResponse format and apply
ResourcePolicy and ExecutionPolicy for security. Session management is integrated
for stateful interactions across ADK run loops.
"""

import json
from datetime import datetime
from typing import Any

from agent_skills.adapters.tool_response import (
    build_error_response,
    build_execution_response,
    build_instructions_response,
    build_metadata_response,
    build_reference_response,
    build_asset_response,
    build_search_response,
)
from agent_skills.models import AuditEvent, SkillState
from agent_skills.resources.reader import FullTextSearcher
from agent_skills.runtime.repository import SkillsRepository
from agent_skills.runtime.session import SkillSessionManager


def _handle_list(
    repository: SkillsRepository,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.list tool invocation.

    Lists all available skills with optional filtering by query string.

    Args:
        repository: SkillsRepository instance
        params: Tool parameters containing optional 'q' filter query

    Returns:
        ToolResponse dict with type="metadata"
    """
    try:
        # Get optional query parameter
        query = params.get("q")

        # Get all skills
        skills = repository.list()

        # Filter by query if provided
        if query:
            query_lower = query.lower()
            skills = [
                skill for skill in skills
                if query_lower in skill.name.lower() or query_lower in skill.description.lower()
            ]

        # Build response
        response = build_metadata_response(
            skill_name="all",
            descriptors=skills,
            meta={"query": query, "count": len(skills)},
        )

        return response.to_dict()

    except Exception as e:
        error_response = build_error_response(
            skill_name="all",
            error=e,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_activate(
    repository: SkillsRepository,
    session_manager: SkillSessionManager,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.activate tool invocation with session management.

    Activates a skill by loading its instructions and creating/updating a session.

    Args:
        repository: SkillsRepository instance
        session_manager: SkillSessionManager for tracking state
        params: Tool parameters containing 'name' (required) and optional 'session_id'

    Returns:
        ToolResponse dict with type="instructions" and session metadata
    """
    skill_name = params.get("name", "")
    session_id = params.get("session_id")

    try:
        # Get or create session
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
        else:
            session = session_manager.create_session(skill_name)

        # Transition to SELECTED if still in DISCOVERED state
        if session.state == SkillState.DISCOVERED:
            session.transition(SkillState.SELECTED)

        # Open skill handle
        handle = repository.open(skill_name)

        # Load instructions (lazy loaded and cached)
        instructions = handle.instructions()

        # Update session state to INSTRUCTIONS_LOADED if not already there
        if session.state != SkillState.INSTRUCTIONS_LOADED:
            session.transition(SkillState.INSTRUCTIONS_LOADED)

        session.add_audit(AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill=skill_name,
            path="SKILL.md",
            bytes=len(instructions.encode("utf-8")),
            sha256=None,  # Will be computed in build_instructions_response
            detail={},
        ))
        session_manager.update_session(session)

        # Build response with session metadata
        response = build_instructions_response(
            skill_name=skill_name,
            instructions=instructions,
            skill_path="SKILL.md",
            meta={
                "session_id": session.session_id,
                "session_state": session.state.value,
            },
        )

        return response.to_dict()

    except Exception as e:
        error_response = build_error_response(
            skill_name=skill_name,
            error=e,
            path="SKILL.md",
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_read(
    repository: SkillsRepository,
    session_manager: SkillSessionManager,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.read tool invocation with session management.

    Reads a file from references/ or assets/ directory and updates session state.

    Args:
        repository: SkillsRepository instance
        session_manager: SkillSessionManager for tracking state
        params: Tool parameters containing 'name', 'path', optional 'max_bytes' and 'session_id'

    Returns:
        ToolResponse dict with type="reference" or "asset" and session metadata
    """
    skill_name = params.get("name", "")
    path = params.get("path", "")
    max_bytes = params.get("max_bytes")
    session_id = params.get("session_id")

    try:
        # Get session if provided
        session = None
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

        # Open skill handle
        handle = repository.open(skill_name)

        # Determine if this is a reference or asset based on path
        if path.startswith("assets/"):
            # Read as asset (binary)
            asset_path = path[7:]  # Remove "assets/" prefix
            content = handle.read_asset(asset_path, max_bytes=max_bytes)

            # Build asset response
            response = build_asset_response(
                skill_name=skill_name,
                asset_path=path,
                content=content,
                truncated=False,  # TODO: Get truncated flag from handle
                meta={},
            )
        else:
            # Read as reference (text)
            # Remove "references/" prefix if present
            ref_path = path[11:] if path.startswith("references/") else path
            content = handle.read_reference(ref_path, max_bytes=max_bytes)

            # Build reference response
            response = build_reference_response(
                skill_name=skill_name,
                reference_path=path if path.startswith("references/") else f"references/{path}",
                content=content,
                truncated=False,  # TODO: Get truncated flag from handle
                meta={},
            )

        # Update session if provided
        if session:
            session.transition(SkillState.RESOURCE_NEEDED)
            session.add_audit(AuditEvent(
                ts=datetime.now(),
                kind="read",
                skill=skill_name,
                path=path,
                bytes=len(content) if isinstance(content, bytes) else len(content.encode("utf-8")),
                sha256=None,  # Already computed in build_*_response
                detail={},
            ))
            session.add_artifact(f"read_{path}", content)
            session_manager.update_session(session)

            # Add session metadata to response
            response.meta["session_id"] = session.session_id
            response.meta["session_state"] = session.state.value

        return response.to_dict()

    except Exception as e:
        error_response = build_error_response(
            skill_name=skill_name,
            error=e,
            path=path,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_run(
    repository: SkillsRepository,
    session_manager: SkillSessionManager,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.run tool invocation with session management.

    Executes a script from scripts/ directory and updates session state.

    Args:
        repository: SkillsRepository instance
        session_manager: SkillSessionManager for tracking state
        params: Tool parameters containing 'name', 'script_path', optional 'args',
                'stdin', 'timeout_s', and 'session_id'

    Returns:
        ToolResponse dict with type="execution_result" and session metadata
    """
    skill_name = params.get("name", "")
    script_path = params.get("script_path", "")
    args = params.get("args")
    stdin = params.get("stdin")
    timeout_s = params.get("timeout_s")
    session_id = params.get("session_id")

    try:
        # Get session if provided
        session = None
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

        # Open skill handle
        handle = repository.open(skill_name)

        # Remove "scripts/" prefix if present
        script_rel_path = script_path[8:] if script_path.startswith("scripts/") else script_path

        # Execute script
        result = handle.run_script(
            relpath=script_rel_path,
            args=args,
            stdin=stdin,
            timeout_s=timeout_s,
        )

        # Build execution response
        response = build_execution_response(
            skill_name=skill_name,
            script_path=script_path if script_path.startswith("scripts/") else f"scripts/{script_path}",
            result=result,
            meta={},
        )

        # Update session if provided
        if session:
            session.transition(SkillState.SCRIPT_NEEDED)
            session.add_audit(AuditEvent(
                ts=datetime.now(),
                kind="run",
                skill=skill_name,
                path=script_path,
                bytes=None,
                sha256=None,
                detail={
                    "args": args,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                },
            ))
            session.add_artifact("execution_result", result.to_dict())
            session_manager.update_session(session)

            # Add session metadata to response
            response.meta["session_id"] = session.session_id
            response.meta["session_state"] = session.state.value

        return response.to_dict()

    except Exception as e:
        error_response = build_error_response(
            skill_name=skill_name,
            error=e,
            path=script_path,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_search(
    repository: SkillsRepository,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.search tool invocation.

    Performs full-text search across all files in a skill's references/ directory.

    Args:
        repository: SkillsRepository instance
        params: Tool parameters containing 'name' and 'query'

    Returns:
        ToolResponse dict with type="search_results"
    """
    skill_name = params.get("name", "")
    query = params.get("query", "")

    try:
        # Open skill handle
        handle = repository.open(skill_name)

        # Get references directory path
        references_dir = handle.descriptor().path / "references"

        # Perform search
        searcher = FullTextSearcher()
        results = searcher.search(
            directory=references_dir,
            query=query,
            max_results=20,
        )

        # Build search response
        response = build_search_response(
            skill_name=skill_name,
            query=query,
            results=results,
            meta={},
        )

        return response.to_dict()

    except Exception as e:
        error_response = build_error_response(
            skill_name=skill_name,
            error=e,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_check_file(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.check_file tool invocation.

    Checks if a file exists and returns its properties.

    Args:
        params: Tool parameters containing 'path'

    Returns:
        ToolResponse dict with type="file_check"
    """
    from pathlib import Path

    path = params.get("path", "")

    try:
        file_path = Path(path)

        # Check for path traversal
        if ".." in str(file_path):
            raise ValueError("Invalid path: directory traversal detected")

        # Get file information
        result = {
            "exists": file_path.exists(),
            "path": str(file_path.resolve()),
        }

        if result["exists"]:
            stat = file_path.stat()
            result["size"] = stat.st_size
            result["is_file"] = file_path.is_file()
            result["is_dir"] = file_path.is_dir()

            if file_path.is_file():
                # Try to determine if readable
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read(1024)  # Try reading first 1KB
                    result["readable"] = True
                    result["encoding"] = "utf-8"
                except (UnicodeDecodeError, PermissionError):
                    result["readable"] = False

        # Build response
        response = {
            "ok": True,
            "type": "file_check",
            "skill": "system",
            "path": path,
            "content": result,
            "bytes": None,
            "sha256": None,
            "truncated": False,
            "meta": {},
        }

        return response

    except Exception as e:
        error_response = build_error_response(
            skill_name="system",
            error=e,
            path=path,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_write_file(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.write_file tool invocation.

    Writes content to a file with validation and safety checks.

    Args:
        params: Tool parameters containing 'path', 'content', and optional 'overwrite'

    Returns:
        ToolResponse dict with type="file_write"
    """
    from pathlib import Path

    path = params.get("path", "")
    content = params.get("content", "")
    overwrite = params.get("overwrite", False)

    try:
        file_path = Path(path)

        # Check for path traversal
        if ".." in str(file_path):
            raise ValueError("Invalid path: directory traversal detected")

        # Check if file exists
        if file_path.exists() and not overwrite:
            raise ValueError(f"File already exists: {path} (use overwrite=true to replace)")

        # Validate JSON if .json extension
        if str(file_path).endswith('.json'):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON content: {e}")

        # Check content size (max 10MB)
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > 10 * 1024 * 1024:
            raise ValueError("Content exceeds maximum size (10MB)")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Verify write
        if not file_path.exists():
            raise ValueError("File write completed but verification failed")

        actual_size = file_path.stat().st_size

        # Build response
        result = {
            "success": True,
            "path": str(file_path.resolve()),
            "bytes_written": len(content_bytes),
            "verified": True,
            "size": actual_size,
        }

        response = {
            "ok": True,
            "type": "file_write",
            "skill": "system",
            "path": path,
            "content": result,
            "bytes": actual_size,
            "sha256": None,
            "truncated": False,
            "meta": {},
        }

        return response

    except Exception as e:
        error_response = build_error_response(
            skill_name="system",
            error=e,
            path=path,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_delete_file(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.delete_file tool invocation.

    Deletes a file with safety checks and confirmation requirement.

    Args:
        params: Tool parameters containing 'path' and 'confirm'

    Returns:
        ToolResponse dict with type="file_delete"
    """
    from pathlib import Path

    path = params.get("path", "")
    confirm = params.get("confirm", False)

    try:
        file_path = Path(path)

        # Check for path traversal
        if ".." in str(file_path):
            raise ValueError("Invalid path: directory traversal detected")

        # Check if confirmation is provided
        if not confirm:
            raise ValueError(
                "Deletion requires confirmation. Set confirm=true to delete the file."
            )

        # Check if file exists
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")

        # Check if it's a directory
        if file_path.is_dir():
            raise ValueError(
                f"Cannot delete directory: {path}. This tool only deletes files."
            )

        # Get file info before deletion
        file_size = file_path.stat().st_size
        resolved_path = str(file_path.resolve())

        # Delete the file
        file_path.unlink()

        # Verify deletion
        if file_path.exists():
            raise ValueError("File deletion completed but verification failed")

        # Build response
        result = {
            "success": True,
            "path": resolved_path,
            "deleted": True,
            "size": file_size,
        }

        response = {
            "ok": True,
            "type": "file_delete",
            "skill": "system",
            "path": path,
            "content": result,
            "bytes": file_size,
            "sha256": None,
            "truncated": False,
            "meta": {},
        }

        return response

    except Exception as e:
        error_response = build_error_response(
            skill_name="system",
            error=e,
            path=path,
            include_traceback=False,
        )
        return error_response.to_dict()


def _handle_list_files(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle skills.list_files tool invocation.

    Lists files and directories in a tree-like structure.

    Args:
        params: Tool parameters containing 'path', optional 'max_depth',
                'show_hidden', and 'include_size'

    Returns:
        ToolResponse dict with type="file_list"
    """
    from pathlib import Path

    path = params.get("path", ".")
    max_depth = params.get("max_depth", 3)
    show_hidden = params.get("show_hidden", False)
    include_size = params.get("include_size", False)

    try:
        root_path = Path(path)

        # Check for path traversal
        if ".." in str(root_path):
            raise ValueError("Invalid path: directory traversal detected")

        # Check if path exists
        if not root_path.exists():
            raise ValueError(f"Path does not exist: {path}")

        def format_size(size_bytes: int) -> str:
            """Format file size in human-readable format."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f}{unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f}TB"

        def walk_directory(dir_path: Path, prefix: str = "", depth: int = 0) -> list[str]:
            """Recursively walk directory and build tree structure."""
            if depth > max_depth:
                return []

            lines = []

            try:
                # Get all items in directory
                items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

                # Filter hidden files if needed
                if not show_hidden:
                    items = [item for item in items if not item.name.startswith('.')]

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "
                    extension = "    " if is_last else "│   "

                    # Build item info
                    item_info = item.name
                    if item.is_dir():
                        item_info += "/"
                    elif include_size and item.is_file():
                        try:
                            size = item.stat().st_size
                            item_info += f" ({format_size(size)})"
                        except (OSError, PermissionError):
                            pass

                    lines.append(f"{prefix}{connector}{item_info}")

                    # Recurse into directories
                    if item.is_dir() and depth < max_depth:
                        sub_lines = walk_directory(item, prefix + extension, depth + 1)
                        lines.extend(sub_lines)

            except PermissionError:
                lines.append(f"{prefix}[Permission Denied]")

            return lines

        # Build tree structure
        if root_path.is_file():
            # Single file
            tree_lines = [str(root_path.name)]
            if include_size:
                size = root_path.stat().st_size
                tree_lines[0] += f" ({format_size(size)})"
        else:
            # Directory tree
            tree_lines = [str(root_path.resolve()) + "/"]
            tree_lines.extend(walk_directory(root_path))

        # Build result
        result = {
            "path": str(root_path.resolve()),
            "is_file": root_path.is_file(),
            "is_dir": root_path.is_dir(),
            "tree": "\n".join(tree_lines),
            "total_lines": len(tree_lines),
        }

        # Build response
        response = {
            "ok": True,
            "type": "file_list",
            "skill": "system",
            "path": path,
            "content": result,
            "bytes": None,
            "sha256": None,
            "truncated": False,
            "meta": {
                "max_depth": max_depth,
                "show_hidden": show_hidden,
                "include_size": include_size,
            },
        }

        return response

    except Exception as e:
        error_response = build_error_response(
            skill_name="system",
            error=e,
            path=path,
            include_traceback=False,
        )
        return error_response.to_dict()


def build_adk_toolset(
    repository: SkillsRepository,
    session_manager: SkillSessionManager | None = None,
) -> list[dict[str, Any]]:
    """Build ADK toolset from repository.

    This function creates all nine skill operation tools configured with
    the provided repository and session manager. The tools can be used
    directly with ADK agents for stateful skill interactions.

    Args:
        repository: SkillsRepository instance with discovered skills
        session_manager: Optional SkillSessionManager for session tracking.
                        If not provided, a new manager will be created.

    Returns:
        List of ADK tool specification dicts, each containing:
        - name: Tool name (e.g., "skills.list")
        - description: Human-readable description
        - input_schema: JSON Schema for tool parameters
        - handler: Callable that takes params dict and returns response dict

    Example:
        >>> from pathlib import Path
        >>> from agent_skills import SkillsRepository
        >>> from agent_skills.adapters.adk import build_adk_toolset
        >>>
        >>> # Initialize repository
        >>> repo = SkillsRepository(roots=[Path("./skills")])
        >>> repo.refresh()
        >>>
        >>> # Build ADK toolset
        >>> tools = build_adk_toolset(repo)
        >>>
        >>> # Use with ADK agent
        >>> agent_config = {
        ...     "tools": tools,
        ...     "system_prompt": repo.to_prompt(format="json"),
        ... }
    """
    # Create session manager if not provided
    if session_manager is None:
        session_manager = SkillSessionManager(repository)

    return [
        {
            "name": "skills.list",
            "description": (
                "List all available skills with metadata (name, description, path, etc.). "
                "Optionally filter by query string matching skill names or descriptions."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Optional filter query to search skill names and descriptions",
                    },
                },
            },
            "handler": lambda params: _handle_list(repository, params),
        },
        {
            "name": "skills.activate",
            "description": (
                "Activate a skill and load its instructions from SKILL.md. "
                "Returns the full markdown body with usage instructions, examples, and guidance. "
                "Creates or updates a session for stateful interaction tracking."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill to activate",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to resume an existing session",
                    },
                },
                "required": ["name"],
            },
            "handler": lambda params: _handle_activate(repository, session_manager, params),
        },
        {
            "name": "skills.read",
            "description": (
                "Read a file from a skill's references/ or assets/ directory. "
                "Provide the skill name and relative path (e.g., 'api-docs.md' for references/api-docs.md). "
                "Text files are returned as strings, binary files as base64-encoded content. "
                "Updates session state if session_id is provided."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill",
                    },
                    "path": {
                        "type": "string",
                        "description": "Relative path to file in references/ or assets/ directory",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Maximum bytes to read (optional)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for state tracking",
                    },
                },
                "required": ["name", "path"],
            },
            "handler": lambda params: _handle_read(repository, session_manager, params),
        },
        {
            "name": "skills.run",
            "description": (
                "Execute a script from a skill's scripts/ directory. "
                "Provide the skill name and relative path (e.g., 'process.py' for scripts/process.py). "
                "Optionally provide command-line arguments, stdin, and timeout. "
                "Returns execution result with exit code, stdout, stderr, and duration. "
                "Updates session state if session_id is provided."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill",
                    },
                    "script_path": {
                        "type": "string",
                        "description": "Relative path to script in scripts/ directory",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command-line arguments for the script",
                    },
                    "stdin": {
                        "type": "string",
                        "description": "Standard input for the script",
                    },
                    "timeout_s": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for state tracking",
                    },
                },
                "required": ["name", "script_path"],
            },
            "handler": lambda params: _handle_run(repository, session_manager, params),
        },
        {
            "name": "skills.search",
            "description": (
                "Search for text in a skill's references/ directory. "
                "Performs case-insensitive full-text search across all reference files. "
                "Returns matching lines with file path, line number, and context."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                },
                "required": ["name", "query"],
            },
            "handler": lambda params: _handle_search(repository, params),
        },
        {
            "name": "skills.check_file",
            "description": (
                "Check if a file exists and get its properties (size, type, etc.). "
                "Returns information about the file including whether it exists, size, and type. "
                "Use this before reading files or after script execution to verify outputs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to check",
                    },
                },
                "required": ["path"],
            },
            "handler": lambda params: _handle_check_file(params),
        },
        {
            "name": "skills.write_file",
            "description": (
                "Write content to a file safely. "
                "Validates JSON content if the file has .json extension. "
                "By default, will not overwrite existing files unless overwrite=true. "
                "Maximum file size is 10MB. Use this to create configuration files, schemas, or any text files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Allow overwriting existing files (default: false)",
                    },
                },
                "required": ["path", "content"],
            },
            "handler": lambda params: _handle_write_file(params),
        },
        {
            "name": "skills.delete_file",
            "description": (
                "Delete a file safely. "
                "Requires confirm=true to actually delete the file. "
                "Will not delete directories. "
                "Use this to remove temporary files, clean up outputs, or delete unwanted files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to delete",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation flag - must be true to delete the file",
                    },
                },
                "required": ["path", "confirm"],
            },
            "handler": lambda params: _handle_delete_file(params),
        },
        {
            "name": "skills.list_files",
            "description": (
                "List files and directories in a tree-like structure. "
                "Recursively walks through directories up to max_depth. "
                "Similar to the 'tree' command. "
                "Use this to explore directory structures and find files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory or file path to list (default: current directory)",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to recurse (default: 3)",
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files (starting with .) (default: false)",
                    },
                    "include_size": {
                        "type": "boolean",
                        "description": "Include file sizes in output (default: false)",
                    },
                },
            },
            "handler": lambda params: _handle_list_files(params),
        },
    ]
