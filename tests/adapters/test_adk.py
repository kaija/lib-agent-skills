"""Tests for ADK adapter.

This module tests the ADK tool specifications and handlers, including:
- Tool structure and schema validation
- Handler functionality for all operations
- Session management integration
- Error handling
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent_skills.adapters.adk import (
    build_adk_toolset,
    _handle_list,
    _handle_activate,
    _handle_read,
    _handle_run,
    _handle_search,
    _handle_check_file,
    _handle_write_file,
    _handle_delete_file,
    _handle_list_files,
)
from agent_skills.exceptions import SkillNotFoundError
from agent_skills.models import ExecutionResult, SkillDescriptor, SkillState
from agent_skills.runtime.repository import SkillsRepository
from agent_skills.runtime.session import SkillSessionManager


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    repo = Mock()

    # Mock list() to return sample skills
    skill1 = SkillDescriptor(
        name="test-skill",
        description="A test skill",
        path=Path("/fake/path/test-skill"),
    )
    skill2 = SkillDescriptor(
        name="another-skill",
        description="Another test skill",
        path=Path("/fake/path/another-skill"),
    )
    repo.list.return_value = [skill1, skill2]

    return repo


@pytest.fixture
def mock_session_manager(mock_repository):
    """Create a real session manager for testing."""
    return SkillSessionManager(mock_repository)


class TestBuildADKToolset:
    """Tests for build_adk_toolset function."""

    def test_returns_list_of_tools(self, mock_repository):
        """Should return a list of tool specifications."""
        tools = build_adk_toolset(mock_repository)

        assert isinstance(tools, list)
        assert len(tools) == 9

    def test_tool_structure(self, mock_repository):
        """Each tool should have required fields."""
        tools = build_adk_toolset(mock_repository)

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "handler" in tool

            # Validate input_schema structure
            assert tool["input_schema"]["type"] == "object"
            assert "properties" in tool["input_schema"]

    def test_tool_names(self, mock_repository):
        """Should create tools with correct names."""
        tools = build_adk_toolset(mock_repository)
        tool_names = [tool["name"] for tool in tools]

        assert "skills.list" in tool_names
        assert "skills.activate" in tool_names
        assert "skills.read" in tool_names
        assert "skills.run" in tool_names
        assert "skills.search" in tool_names
        assert "skills.check_file" in tool_names
        assert "skills.write_file" in tool_names
        assert "skills.delete_file" in tool_names
        assert "skills.list_files" in tool_names

    def test_creates_session_manager_if_not_provided(self, mock_repository):
        """Should create a session manager if none provided."""
        tools = build_adk_toolset(mock_repository)

        # Should not raise an error
        assert len(tools) == 9

    def test_uses_provided_session_manager(self, mock_repository, mock_session_manager):
        """Should use provided session manager."""
        tools = build_adk_toolset(mock_repository, mock_session_manager)

        # Should not raise an error
        assert len(tools) == 9


class TestHandleList:
    """Tests for _handle_list handler."""

    def test_returns_all_skills(self, mock_repository):
        """Should return all skills when no query provided."""
        params = {}
        result = _handle_list(mock_repository, params)

        assert result["ok"] is True
        assert result["type"] == "metadata"
        assert result["skill"] == "all"
        assert len(result["content"]) == 2
        assert result["meta"]["count"] == 2

    def test_filters_by_query(self, mock_repository):
        """Should filter skills by query string."""
        params = {"q": "another"}
        result = _handle_list(mock_repository, params)

        assert result["ok"] is True
        assert len(result["content"]) == 1
        assert result["content"][0]["name"] == "another-skill"
        assert result["meta"]["query"] == "another"

    def test_case_insensitive_filtering(self, mock_repository):
        """Should perform case-insensitive filtering."""
        params = {"q": "ANOTHER"}
        result = _handle_list(mock_repository, params)

        assert result["ok"] is True
        assert len(result["content"]) == 1
        assert result["content"][0]["name"] == "another-skill"

    def test_handles_errors(self, mock_repository):
        """Should return error response on exception."""
        mock_repository.list.side_effect = Exception("Test error")

        params = {}
        result = _handle_list(mock_repository, params)

        assert result["ok"] is False
        assert result["type"] == "error"
        assert "Test error" in result["content"]


class TestHandleActivate:
    """Tests for _handle_activate handler."""

    def test_activates_skill_and_creates_session(self, mock_repository, mock_session_manager):
        """Should activate skill and create new session."""
        # Mock handle
        mock_handle = Mock()
        mock_handle.instructions.return_value = "# Test Instructions"
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill"}
        result = _handle_activate(mock_repository, mock_session_manager, params)

        if not result["ok"]:
            print(f"Error: {result}")
        assert result["ok"] is True
        assert result["type"] == "instructions"
        assert result["skill"] == "test-skill"
        assert result["content"] == "# Test Instructions"
        assert "session_id" in result["meta"]
        assert result["meta"]["session_state"] == "instructions_loaded"

        # Verify session was created
        sessions = mock_session_manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].skill_name == "test-skill"
        assert sessions[0].state == SkillState.INSTRUCTIONS_LOADED

    def test_resumes_existing_session(self, mock_repository, mock_session_manager):
        """Should resume existing session if session_id provided."""
        # Create initial session
        session = mock_session_manager.create_session("test-skill")

        # Mock handle
        mock_handle = Mock()
        mock_handle.instructions.return_value = "# Test Instructions"
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "session_id": session.session_id}
        result = _handle_activate(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["meta"]["session_id"] == session.session_id

        # Should still have only one session
        sessions = mock_session_manager.list_sessions()
        assert len(sessions) == 1

    def test_handles_invalid_session_id(self, mock_repository, mock_session_manager):
        """Should return error for invalid session_id."""
        params = {"name": "test-skill", "session_id": "invalid-id"}
        result = _handle_activate(mock_repository, mock_session_manager, params)

        assert result["ok"] is False
        assert result["type"] == "error"
        assert "Session not found" in result["content"]

    def test_handles_skill_not_found(self, mock_repository, mock_session_manager):
        """Should return error when skill not found."""
        mock_repository.open.side_effect = SkillNotFoundError("Skill not found")

        params = {"name": "nonexistent"}
        result = _handle_activate(mock_repository, mock_session_manager, params)

        assert result["ok"] is False
        assert result["type"] == "error"
        assert "SkillNotFoundError" in result["content"]


class TestHandleRead:
    """Tests for _handle_read handler."""

    def test_reads_reference_file(self, mock_repository, mock_session_manager):
        """Should read reference file and return content."""
        # Mock handle
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "Reference content"
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "path": "api-docs.md"}
        result = _handle_read(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["type"] == "reference"
        assert result["skill"] == "test-skill"
        assert result["content"] == "Reference content"
        assert "references/" in result["path"]

    def test_reads_asset_file(self, mock_repository, mock_session_manager):
        """Should read asset file and return binary content."""
        # Mock handle
        mock_handle = Mock()
        mock_handle.read_asset.return_value = b"Binary content"
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "path": "assets/image.png"}
        result = _handle_read(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["type"] == "asset"
        assert result["skill"] == "test-skill"
        # Binary content is base64 encoded in the response
        import base64
        assert result["content"] == base64.b64encode(b"Binary content").decode("utf-8")

    def test_updates_session_state(self, mock_repository, mock_session_manager):
        """Should update session state when session_id provided."""
        # Create session and transition to INSTRUCTIONS_LOADED
        session = mock_session_manager.create_session("test-skill")
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        mock_session_manager.update_session(session)

        # Mock handle
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "Content"
        mock_repository.open.return_value = mock_handle

        params = {
            "name": "test-skill",
            "path": "api-docs.md",
            "session_id": session.session_id,
        }
        result = _handle_read(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["meta"]["session_id"] == session.session_id
        assert result["meta"]["session_state"] == "resource_needed"

        # Verify session was updated
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.state == SkillState.RESOURCE_NEEDED
        assert len(updated_session.audit) > 0

    def test_handles_max_bytes_parameter(self, mock_repository, mock_session_manager):
        """Should pass max_bytes parameter to read methods."""
        # Mock handle
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "Content"
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "path": "api-docs.md", "max_bytes": 1000}
        result = _handle_read(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        mock_handle.read_reference.assert_called_once_with("api-docs.md", max_bytes=1000)


class TestHandleRun:
    """Tests for _handle_run handler."""

    def test_executes_script(self, mock_repository, mock_session_manager):
        """Should execute script and return result."""
        # Mock handle and execution result
        mock_handle = Mock()
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration_ms=100,
            meta={"sandbox": "local"},
        )
        mock_handle.run_script.return_value = exec_result
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "script_path": "process.py"}
        result = _handle_run(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["type"] == "execution_result"
        assert result["skill"] == "test-skill"
        assert result["content"]["exit_code"] == 0
        assert result["content"]["stdout"] == "Success"

    def test_passes_script_arguments(self, mock_repository, mock_session_manager):
        """Should pass arguments to script execution."""
        # Mock handle
        mock_handle = Mock()
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_handle.run_script.return_value = exec_result
        mock_repository.open.return_value = mock_handle

        params = {
            "name": "test-skill",
            "script_path": "process.py",
            "args": ["--input", "data.csv"],
            "stdin": "test input",
            "timeout_s": 30,
        }
        result = _handle_run(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        mock_handle.run_script.assert_called_once_with(
            relpath="process.py",
            args=["--input", "data.csv"],
            stdin="test input",
            timeout_s=30,
        )

    def test_updates_session_state(self, mock_repository, mock_session_manager):
        """Should update session state when session_id provided."""
        # Create session and transition to INSTRUCTIONS_LOADED
        session = mock_session_manager.create_session("test-skill")
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        mock_session_manager.update_session(session)

        # Mock handle
        mock_handle = Mock()
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_handle.run_script.return_value = exec_result
        mock_repository.open.return_value = mock_handle

        params = {
            "name": "test-skill",
            "script_path": "process.py",
            "session_id": session.session_id,
        }
        result = _handle_run(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        assert result["meta"]["session_id"] == session.session_id
        assert result["meta"]["session_state"] == "script_needed"

        # Verify session was updated
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.state == SkillState.SCRIPT_NEEDED
        assert "execution_result" in updated_session.artifacts

    def test_handles_script_path_prefix(self, mock_repository, mock_session_manager):
        """Should handle scripts/ prefix in path."""
        # Mock handle
        mock_handle = Mock()
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_handle.run_script.return_value = exec_result
        mock_repository.open.return_value = mock_handle

        params = {"name": "test-skill", "script_path": "scripts/process.py"}
        result = _handle_run(mock_repository, mock_session_manager, params)

        assert result["ok"] is True
        # Should remove scripts/ prefix when calling run_script
        mock_handle.run_script.assert_called_once()
        call_args = mock_handle.run_script.call_args
        assert call_args[1]["relpath"] == "process.py"


class TestHandleSearch:
    """Tests for _handle_search handler."""

    def test_searches_references(self, mock_repository):
        """Should search references directory and return results."""
        # Mock handle and descriptor
        mock_handle = Mock()
        mock_descriptor = Mock()
        mock_descriptor.path = Path("/fake/path/test-skill")
        mock_handle.descriptor.return_value = mock_descriptor
        mock_repository.open.return_value = mock_handle

        # Mock searcher
        with patch("agent_skills.adapters.adk.FullTextSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search.return_value = [
                {"path": "api-docs.md", "line_num": 10, "context": "authentication"},
            ]
            mock_searcher_class.return_value = mock_searcher

            params = {"name": "test-skill", "query": "authentication"}
            result = _handle_search(mock_repository, params)

        assert result["ok"] is True
        assert result["type"] == "search_results"
        assert result["skill"] == "test-skill"
        assert len(result["content"]) == 1
        assert result["meta"]["query"] == "authentication"
        assert result["meta"]["result_count"] == 1

    def test_handles_no_results(self, mock_repository):
        """Should handle case with no search results."""
        # Mock handle and descriptor
        mock_handle = Mock()
        mock_descriptor = Mock()
        mock_descriptor.path = Path("/fake/path/test-skill")
        mock_handle.descriptor.return_value = mock_descriptor
        mock_repository.open.return_value = mock_handle

        # Mock searcher with no results
        with patch("agent_skills.adapters.adk.FullTextSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search.return_value = []
            mock_searcher_class.return_value = mock_searcher

            params = {"name": "test-skill", "query": "nonexistent"}
            result = _handle_search(mock_repository, params)

        assert result["ok"] is True
        assert len(result["content"]) == 0
        assert result["meta"]["result_count"] == 0

    def test_handles_errors(self, mock_repository):
        """Should return error response on exception."""
        mock_repository.open.side_effect = Exception("Test error")

        params = {"name": "test-skill", "query": "test"}
        result = _handle_search(mock_repository, params)

        assert result["ok"] is False
        assert result["type"] == "error"
        assert "Test error" in result["content"]


class TestIntegration:
    """Integration tests for ADK adapter."""

    def test_full_workflow_with_session(self, mock_repository, mock_session_manager):
        """Should support full workflow with session management."""
        # Mock handle
        mock_handle = Mock()
        mock_handle.instructions.return_value = "# Instructions"
        mock_handle.read_reference.return_value = "Reference content"
        exec_result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_handle.run_script.return_value = exec_result
        mock_repository.open.return_value = mock_handle

        # 1. Activate skill (creates session)
        result1 = _handle_activate(mock_repository, mock_session_manager, {"name": "test-skill"})
        assert result1["ok"] is True
        session_id = result1["meta"]["session_id"]

        # 2. Read reference (updates session)
        result2 = _handle_read(
            mock_repository,
            mock_session_manager,
            {"name": "test-skill", "path": "api-docs.md", "session_id": session_id},
        )
        assert result2["ok"] is True
        assert result2["meta"]["session_state"] == "resource_needed"

        # 3. Run script (updates session)
        result3 = _handle_run(
            mock_repository,
            mock_session_manager,
            {"name": "test-skill", "script_path": "process.py", "session_id": session_id},
        )
        assert result3["ok"] is True
        assert result3["meta"]["session_state"] == "script_needed"

        # Verify session has complete audit trail
        session = mock_session_manager.get_session(session_id)
        assert len(session.audit) == 3  # activate, read, run
        assert len(session.artifacts) == 2  # read content, execution result



class TestHandleCheckFile:
    """Tests for _handle_check_file handler."""

    def test_checks_existing_file(self, tmp_path):
        """Should check if a file exists and return its properties."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = _handle_check_file({"path": str(test_file)})

        assert result["ok"] is True
        assert result["type"] == "file_check"
        assert result["content"]["exists"] is True
        assert result["content"]["is_file"] is True
        assert result["content"]["size"] == 12  # "test content" length

    def test_checks_nonexistent_file(self, tmp_path):
        """Should return exists=false for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"

        result = _handle_check_file({"path": str(nonexistent)})

        assert result["ok"] is True
        assert result["content"]["exists"] is False

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        result = _handle_check_file({"path": "../../../etc/passwd"})

        assert result["ok"] is False
        assert "traversal" in result["content"].lower()


class TestHandleWriteFile:
    """Tests for _handle_write_file handler."""

    def test_writes_file_successfully(self, tmp_path):
        """Should write content to a file."""
        test_file = tmp_path / "output.txt"

        result = _handle_write_file({
            "path": str(test_file),
            "content": "Hello, World!",
        })

        assert result["ok"] is True
        assert result["type"] == "file_write"
        assert result["content"]["success"] is True
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"

    def test_validates_json_content(self, tmp_path):
        """Should validate JSON content for .json files."""
        test_file = tmp_path / "data.json"

        # Valid JSON
        result = _handle_write_file({
            "path": str(test_file),
            "content": '{"key": "value"}',
        })
        assert result["ok"] is True

        # Invalid JSON
        result = _handle_write_file({
            "path": str(tmp_path / "invalid.json"),
            "content": '{invalid json}',
        })
        assert result["ok"] is False
        assert "json" in result["content"].lower()

    def test_prevents_overwrite_by_default(self, tmp_path):
        """Should not overwrite existing files by default."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("original")

        result = _handle_write_file({
            "path": str(test_file),
            "content": "new content",
        })

        assert result["ok"] is False
        assert "already exists" in result["content"].lower()
        assert test_file.read_text() == "original"

    def test_allows_overwrite_when_specified(self, tmp_path):
        """Should overwrite when overwrite=true."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("original")

        result = _handle_write_file({
            "path": str(test_file),
            "content": "new content",
            "overwrite": True,
        })

        assert result["ok"] is True
        assert test_file.read_text() == "new content"

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        result = _handle_write_file({
            "path": "../../../tmp/malicious.txt",
            "content": "bad content",
        })

        assert result["ok"] is False
        assert "traversal" in result["content"].lower()


class TestHandleDeleteFile:
    """Tests for _handle_delete_file handler."""

    def test_deletes_file_with_confirmation(self, tmp_path):
        """Should delete file when confirm=true."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        result = _handle_delete_file({
            "path": str(test_file),
            "confirm": True,
        })

        assert result["ok"] is True
        assert result["type"] == "file_delete"
        assert result["content"]["deleted"] is True
        assert not test_file.exists()

    def test_requires_confirmation(self, tmp_path):
        """Should require confirm=true to delete."""
        test_file = tmp_path / "protected.txt"
        test_file.write_text("protected")

        result = _handle_delete_file({
            "path": str(test_file),
            "confirm": False,
        })

        assert result["ok"] is False
        assert "confirmation" in result["content"].lower()
        assert test_file.exists()

    def test_handles_nonexistent_file(self, tmp_path):
        """Should handle nonexistent file gracefully."""
        nonexistent = tmp_path / "nonexistent.txt"

        result = _handle_delete_file({
            "path": str(nonexistent),
            "confirm": True,
        })

        assert result["ok"] is False
        assert "does not exist" in result["content"].lower()

    def test_prevents_directory_deletion(self, tmp_path):
        """Should not delete directories."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        result = _handle_delete_file({
            "path": str(test_dir),
            "confirm": True,
        })

        assert result["ok"] is False
        assert "directory" in result["content"].lower()
        assert test_dir.exists()

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        result = _handle_delete_file({
            "path": "../../../etc/passwd",
            "confirm": True,
        })

        assert result["ok"] is False
        assert "traversal" in result["content"].lower()



class TestHandleListFiles:
    """Tests for _handle_list_files handler."""

    def test_lists_directory_tree(self, tmp_path):
        """Should list directory structure in tree format."""
        # Create test structure
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        result = _handle_list_files({"path": str(tmp_path)})

        assert result["ok"] is True
        assert result["type"] == "file_list"
        assert result["content"]["is_dir"] is True
        assert "file1.txt" in result["content"]["tree"]
        assert "file2.txt" in result["content"]["tree"]
        assert "subdir/" in result["content"]["tree"]
        assert "file3.txt" in result["content"]["tree"]

    def test_lists_single_file(self, tmp_path):
        """Should handle single file."""
        test_file = tmp_path / "single.txt"
        test_file.write_text("content")

        result = _handle_list_files({"path": str(test_file)})

        assert result["ok"] is True
        assert result["content"]["is_file"] is True
        assert "single.txt" in result["content"]["tree"]

    def test_respects_max_depth(self, tmp_path):
        """Should respect max_depth parameter."""
        # Create nested structure
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "level3").mkdir()
        (tmp_path / "level1" / "level2" / "level3" / "deep.txt").write_text("deep")

        # With max_depth=1, should not see level3
        result = _handle_list_files({"path": str(tmp_path), "max_depth": 1})

        assert result["ok"] is True
        assert "level1/" in result["content"]["tree"]
        assert "level2/" in result["content"]["tree"]
        # level3 should not appear due to depth limit

    def test_hides_hidden_files_by_default(self, tmp_path):
        """Should hide hidden files by default."""
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden.txt").write_text("hidden")

        result = _handle_list_files({"path": str(tmp_path)})

        assert result["ok"] is True
        assert "visible.txt" in result["content"]["tree"]
        assert ".hidden.txt" not in result["content"]["tree"]

    def test_shows_hidden_files_when_requested(self, tmp_path):
        """Should show hidden files when show_hidden=true."""
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden.txt").write_text("hidden")

        result = _handle_list_files({
            "path": str(tmp_path),
            "show_hidden": True
        })

        assert result["ok"] is True
        assert "visible.txt" in result["content"]["tree"]
        assert ".hidden.txt" in result["content"]["tree"]

    def test_includes_file_sizes_when_requested(self, tmp_path):
        """Should include file sizes when include_size=true."""
        (tmp_path / "file.txt").write_text("test content")

        result = _handle_list_files({
            "path": str(tmp_path),
            "include_size": True
        })

        assert result["ok"] is True
        # Should contain size information
        assert "B)" in result["content"]["tree"] or "KB)" in result["content"]["tree"]

    def test_handles_nonexistent_path(self):
        """Should handle nonexistent path gracefully."""
        result = _handle_list_files({"path": "/nonexistent/path"})

        assert result["ok"] is False
        assert "does not exist" in result["content"].lower()

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        result = _handle_list_files({"path": "../../../etc"})

        assert result["ok"] is False
        assert "traversal" in result["content"].lower()
