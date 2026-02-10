"""Unit tests for LangChain adapter.

These tests verify that the LangChain tools correctly integrate with the
SkillsRepository and return properly formatted ToolResponse objects.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Skip all tests if langchain is not installed
pytest.importorskip("langchain")

from agent_skills.adapters.langchain import (
    SkillsActivateTool,
    SkillsListTool,
    SkillsReadTool,
    SkillsRunTool,
    SkillsSearchTool,
    build_langchain_tools,
)
from agent_skills.exceptions import SkillNotFoundError
from agent_skills.models import (
    ExecutionPolicy,
    ExecutionResult,
    ResourcePolicy,
    SkillDescriptor,
)
from agent_skills.runtime.repository import SkillsRepository


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    # Use Mock without spec to avoid Python 3.14 type annotation issues
    repo = Mock()
    return repo


@pytest.fixture
def sample_skills():
    """Create sample skill descriptors for testing."""
    return [
        SkillDescriptor(
            name="data-processor",
            description="Process CSV data",
            path=Path("/skills/data-processor"),
            hash="abc123",
            mtime=1234567890.0,
        ),
        SkillDescriptor(
            name="api-client",
            description="Call external APIs",
            path=Path("/skills/api-client"),
            hash="def456",
            mtime=1234567891.0,
        ),
    ]


class TestSkillsListTool:
    """Tests for SkillsListTool."""

    def test_tool_properties(self, mock_repository):
        """Test that tool has correct name and description."""
        tool = SkillsListTool(repository=mock_repository)

        assert tool.name == "skills_list"
        assert "List all available skills" in tool.description
        assert tool.repository is mock_repository

    def test_list_all_skills(self, mock_repository, sample_skills):
        """Test listing all skills without filter."""
        mock_repository.list.return_value = sample_skills
        tool = SkillsListTool(repository=mock_repository)

        result = tool._run()

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["type"] == "metadata"
        assert response["skill"] == "all"
        assert len(response["content"]) == 2
        assert response["content"][0]["name"] == "data-processor"
        assert response["content"][1]["name"] == "api-client"
        assert response["meta"]["count"] == 2

        mock_repository.list.assert_called_once()

    def test_list_with_filter(self, mock_repository, sample_skills):
        """Test listing skills with query filter."""
        mock_repository.list.return_value = sample_skills
        tool = SkillsListTool(repository=mock_repository)

        result = tool._run(q="data")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert len(response["content"]) == 1
        assert response["content"][0]["name"] == "data-processor"
        assert response["meta"]["query"] == "data"
        assert response["meta"]["count"] == 1

    def test_list_with_filter_no_matches(self, mock_repository, sample_skills):
        """Test listing skills with filter that matches nothing."""
        mock_repository.list.return_value = sample_skills
        tool = SkillsListTool(repository=mock_repository)

        result = tool._run(q="nonexistent")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert len(response["content"]) == 0
        assert response["meta"]["count"] == 0

    def test_list_empty_repository(self, mock_repository):
        """Test listing skills when repository is empty."""
        mock_repository.list.return_value = []
        tool = SkillsListTool(repository=mock_repository)

        result = tool._run()

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["content"] == []
        assert response["meta"]["count"] == 0

    def test_list_with_exception(self, mock_repository):
        """Test that exceptions are converted to error responses."""
        mock_repository.list.side_effect = RuntimeError("Database error")
        tool = SkillsListTool(repository=mock_repository)

        result = tool._run()

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is False
        assert response["type"] == "error"
        assert "RuntimeError" in response["content"]
        assert "Database error" in response["content"]


class TestSkillsActivateTool:
    """Tests for SkillsActivateTool."""

    def test_tool_properties(self, mock_repository):
        """Test that tool has correct name and description."""
        tool = SkillsActivateTool(repository=mock_repository)

        assert tool.name == "skills_activate"
        assert "Activate a skill" in tool.description
        assert tool.repository is mock_repository

    def test_activate_skill(self, mock_repository):
        """Test activating a skill and loading instructions."""
        mock_handle = Mock()
        mock_handle.instructions.return_value = "# Data Processor\n\nProcess CSV files."
        mock_repository.open.return_value = mock_handle

        tool = SkillsActivateTool(repository=mock_repository)
        result = tool._run(name="data-processor")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["type"] == "instructions"
        assert response["skill"] == "data-processor"
        assert response["path"] == "SKILL.md"
        assert "# Data Processor" in response["content"]
        assert response["bytes"] > 0
        assert response["sha256"] is not None
        assert response["truncated"] is False

        mock_repository.open.assert_called_once_with("data-processor")
        mock_handle.instructions.assert_called_once()

    def test_activate_skill_empty_instructions(self, mock_repository):
        """Test activating a skill with empty instructions."""
        mock_handle = Mock()
        mock_handle.instructions.return_value = ""
        mock_repository.open.return_value = mock_handle

        tool = SkillsActivateTool(repository=mock_repository)
        result = tool._run(name="empty-skill")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["content"] == ""
        assert response["bytes"] == 0

    def test_activate_nonexistent_skill(self, mock_repository):
        """Test activating a skill that doesn't exist."""
        mock_repository.open.side_effect = SkillNotFoundError("Skill 'nonexistent' not found")

        tool = SkillsActivateTool(repository=mock_repository)
        result = tool._run(name="nonexistent")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is False
        assert response["type"] == "error"
        assert response["skill"] == "nonexistent"
        assert "SkillNotFoundError" in response["content"]
        assert "not found" in response["content"]


class TestSkillsReadTool:
    """Tests for SkillsReadTool."""

    def test_tool_properties(self, mock_repository):
        """Test that tool has correct name and description."""
        tool = SkillsReadTool(repository=mock_repository)

        assert tool.name == "skills_read"
        assert "Read a file" in tool.description
        assert tool.repository is mock_repository

    def test_read_reference_file(self, mock_repository):
        """Test reading a reference file."""
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "# API Documentation\n\nEndpoints..."
        mock_repository.open.return_value = mock_handle

        tool = SkillsReadTool(repository=mock_repository)
        result = tool._run(name="data-processor", path="api-docs.md")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["type"] == "reference"
        assert response["skill"] == "data-processor"
        assert "references/" in response["path"]
        assert "# API Documentation" in response["content"]
        assert response["bytes"] > 0
        assert response["sha256"] is not None

        mock_handle.read_reference.assert_called_once_with("api-docs.md", max_bytes=None)

    def test_read_reference_with_prefix(self, mock_repository):
        """Test reading a reference file with references/ prefix."""
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "Content"
        mock_repository.open.return_value = mock_handle

        tool = SkillsReadTool(repository=mock_repository)
        result = tool._run(name="data-processor", path="references/api-docs.md")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["path"] == "references/api-docs.md"

        # Should strip the prefix when calling read_reference
        mock_handle.read_reference.assert_called_once_with("api-docs.md", max_bytes=None)

    def test_read_asset_file(self, mock_repository):
        """Test reading an asset file."""
        mock_handle = Mock()
        mock_handle.read_asset.return_value = b"\x89PNG\r\n\x1a\n"
        mock_repository.open.return_value = mock_handle

        tool = SkillsReadTool(repository=mock_repository)
        result = tool._run(name="data-processor", path="assets/diagram.png")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["type"] == "asset"
        assert response["skill"] == "data-processor"
        assert response["path"] == "assets/diagram.png"
        # Binary content should be base64 encoded in JSON
        assert isinstance(response["content"], str)
        assert response["bytes"] > 0

        mock_handle.read_asset.assert_called_once_with("diagram.png", max_bytes=None)

    def test_read_with_max_bytes(self, mock_repository):
        """Test reading a file with max_bytes limit."""
        mock_handle = Mock()
        mock_handle.read_reference.return_value = "Content"
        mock_repository.open.return_value = mock_handle

        tool = SkillsReadTool(repository=mock_repository)
        result = tool._run(name="data-processor", path="api-docs.md", max_bytes=1000)

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True

        mock_handle.read_reference.assert_called_once_with("api-docs.md", max_bytes=1000)

    def test_read_nonexistent_file(self, mock_repository):
        """Test reading a file that doesn't exist."""
        mock_handle = Mock()
        mock_handle.read_reference.side_effect = FileNotFoundError("File not found")
        mock_repository.open.return_value = mock_handle

        tool = SkillsReadTool(repository=mock_repository)
        result = tool._run(name="data-processor", path="nonexistent.md")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is False
        assert response["type"] == "error"
        assert "FileNotFoundError" in response["content"]


class TestSkillsRunTool:
    """Tests for SkillsRunTool."""

    def test_tool_properties(self, mock_repository):
        """Test that tool has correct name and description."""
        tool = SkillsRunTool(repository=mock_repository)

        assert tool.name == "skills_run"
        assert "Execute a script" in tool.description
        assert tool.repository is mock_repository

    def test_run_script_success(self, mock_repository):
        """Test running a script successfully."""
        mock_handle = Mock()
        mock_handle.run_script.return_value = ExecutionResult(
            exit_code=0,
            stdout="Processing complete\n",
            stderr="",
            duration_ms=1234,
            meta={"sandbox": "local_subprocess"},
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(
            name="data-processor",
            script_path="process.py",
            args=["--input", "data.csv"],
        )

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["type"] == "execution_result"
        assert response["skill"] == "data-processor"
        assert "scripts/" in response["path"]
        assert response["content"]["exit_code"] == 0
        assert response["content"]["stdout"] == "Processing complete\n"
        assert response["content"]["duration_ms"] == 1234

        mock_handle.run_script.assert_called_once_with(
            relpath="process.py",
            args=["--input", "data.csv"],
            stdin=None,
            timeout_s=None,
        )

    def test_run_script_with_prefix(self, mock_repository):
        """Test running a script with scripts/ prefix."""
        mock_handle = Mock()
        mock_handle.run_script.return_value = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(name="data-processor", script_path="scripts/process.py")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True
        assert response["path"] == "scripts/process.py"

        # Should strip the prefix when calling run_script
        mock_handle.run_script.assert_called_once_with(
            relpath="process.py",
            args=None,
            stdin=None,
            timeout_s=None,
        )

    def test_run_script_with_stdin(self, mock_repository):
        """Test running a script with stdin."""
        mock_handle = Mock()
        mock_handle.run_script.return_value = ExecutionResult(
            exit_code=0,
            stdout="Processed input\n",
            stderr="",
            duration_ms=500,
            meta={},
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(
            name="data-processor",
            script_path="process.py",
            stdin="input data",
        )

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True

        mock_handle.run_script.assert_called_once_with(
            relpath="process.py",
            args=None,
            stdin="input data",
            timeout_s=None,
        )

    def test_run_script_with_timeout(self, mock_repository):
        """Test running a script with custom timeout."""
        mock_handle = Mock()
        mock_handle.run_script.return_value = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            meta={},
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(
            name="data-processor",
            script_path="process.py",
            timeout_s=30,
        )

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is True

        mock_handle.run_script.assert_called_once_with(
            relpath="process.py",
            args=None,
            stdin=None,
            timeout_s=30,
        )

    def test_run_script_failure(self, mock_repository):
        """Test running a script that fails."""
        mock_handle = Mock()
        mock_handle.run_script.return_value = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error: File not found\n",
            duration_ms=100,
            meta={},
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(name="data-processor", script_path="process.py")

        # Parse JSON response
        response = json.loads(result)

        # Non-zero exit code is still ok=True, just with exit_code != 0
        assert response["ok"] is True
        assert response["content"]["exit_code"] == 1
        assert "Error: File not found" in response["content"]["stderr"]

    def test_run_script_exception(self, mock_repository):
        """Test running a script that raises an exception."""
        from agent_skills.exceptions import ScriptExecutionDisabledError

        mock_handle = Mock()
        mock_handle.run_script.side_effect = ScriptExecutionDisabledError(
            "Script execution is disabled"
        )
        mock_repository.open.return_value = mock_handle

        tool = SkillsRunTool(repository=mock_repository)
        result = tool._run(name="data-processor", script_path="process.py")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is False
        assert response["type"] == "error"
        assert "ScriptExecutionDisabledError" in response["content"]


class TestSkillsSearchTool:
    """Tests for SkillsSearchTool."""

    def test_tool_properties(self, mock_repository):
        """Test that tool has correct name and description."""
        tool = SkillsSearchTool(repository=mock_repository)

        assert tool.name == "skills_search"
        assert "Search for text" in tool.description
        assert tool.repository is mock_repository

    def test_search_with_results(self, mock_repository):
        """Test searching with results found."""
        mock_handle = Mock()
        mock_descriptor = Mock()
        mock_descriptor.path = Path("/skills/data-processor")
        mock_handle.descriptor.return_value = mock_descriptor
        mock_repository.open.return_value = mock_handle

        # Mock the FullTextSearcher
        with patch("agent_skills.adapters.langchain.FullTextSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search.return_value = [
                {
                    "path": "api-docs.md",
                    "line_num": 42,
                    "context": "...authentication token...",
                },
                {
                    "path": "guide.md",
                    "line_num": 15,
                    "context": "...token validation...",
                },
            ]
            mock_searcher_class.return_value = mock_searcher

            tool = SkillsSearchTool(repository=mock_repository)
            result = tool._run(name="data-processor", query="token")

            # Parse JSON response
            response = json.loads(result)

            assert response["ok"] is True
            assert response["type"] == "search_results"
            assert response["skill"] == "data-processor"
            assert len(response["content"]) == 2
            assert response["content"][0]["path"] == "api-docs.md"
            assert response["content"][0]["line_num"] == 42
            assert response["meta"]["query"] == "token"
            assert response["meta"]["result_count"] == 2

            # Verify searcher was called correctly
            mock_searcher.search.assert_called_once_with(
                directory=Path("/skills/data-processor/references"),
                query="token",
                max_results=20,
            )

    def test_search_no_results(self, mock_repository):
        """Test searching with no results found."""
        mock_handle = Mock()
        mock_descriptor = Mock()
        mock_descriptor.path = Path("/skills/data-processor")
        mock_handle.descriptor.return_value = mock_descriptor
        mock_repository.open.return_value = mock_handle

        with patch("agent_skills.adapters.langchain.FullTextSearcher") as mock_searcher_class:
            mock_searcher = Mock()
            mock_searcher.search.return_value = []
            mock_searcher_class.return_value = mock_searcher

            tool = SkillsSearchTool(repository=mock_repository)
            result = tool._run(name="data-processor", query="nonexistent")

            # Parse JSON response
            response = json.loads(result)

            assert response["ok"] is True
            assert response["content"] == []
            assert response["meta"]["result_count"] == 0

    def test_search_exception(self, mock_repository):
        """Test search with exception."""
        mock_repository.open.side_effect = SkillNotFoundError("Skill not found")

        tool = SkillsSearchTool(repository=mock_repository)
        result = tool._run(name="nonexistent", query="test")

        # Parse JSON response
        response = json.loads(result)

        assert response["ok"] is False
        assert response["type"] == "error"
        assert "SkillNotFoundError" in response["content"]


class TestBuildLangchainTools:
    """Tests for build_langchain_tools function."""

    def test_build_all_tools(self, mock_repository):
        """Test that build_langchain_tools creates all 9 tools."""
        tools = build_langchain_tools(mock_repository)

        assert len(tools) == 9

        # Check tool types
        tool_names = [tool.name for tool in tools]
        assert "skills_list" in tool_names
        assert "skills_activate" in tool_names
        assert "skills_read" in tool_names
        assert "skills_run" in tool_names
        assert "skills_search" in tool_names
        assert "skills_check_file" in tool_names
        assert "skills_write_file" in tool_names
        assert "skills_delete_file" in tool_names
        assert "skills_list_files" in tool_names

    def test_tools_share_repository(self, mock_repository):
        """Test that all tools share the same repository instance."""
        tools = build_langchain_tools(mock_repository)

        for tool in tools:
            assert tool.repository is mock_repository

    def test_tools_are_base_tool_instances(self, mock_repository):
        """Test that all tools are BaseTool instances."""
        from langchain.tools import BaseTool

        tools = build_langchain_tools(mock_repository)

        for tool in tools:
            assert isinstance(tool, BaseTool)

    def test_tools_have_input_schemas(self, mock_repository):
        """Test that all tools have Pydantic input schemas."""
        from pydantic import BaseModel

        tools = build_langchain_tools(mock_repository)

        for tool in tools:
            assert hasattr(tool, "args_schema")
            assert issubclass(tool.args_schema, BaseModel)


class TestLangChainIntegration:
    """Integration tests for LangChain adapter."""

    def test_tool_can_be_called_directly(self, mock_repository, sample_skills):
        """Test that tools can be called directly (not just through LangChain)."""
        mock_repository.list.return_value = sample_skills

        tool = SkillsListTool(repository=mock_repository)
        result = tool._run()

        # Should return valid JSON
        response = json.loads(result)
        assert response["ok"] is True
        assert len(response["content"]) == 2

    def test_tool_response_is_json_serializable(self, mock_repository, sample_skills):
        """Test that all tool responses are JSON serializable."""
        mock_repository.list.return_value = sample_skills

        tool = SkillsListTool(repository=mock_repository)
        result = tool._run()

        # Should be able to parse and re-serialize
        response = json.loads(result)
        re_serialized = json.dumps(response)
        assert isinstance(re_serialized, str)

    def test_error_responses_are_json_serializable(self, mock_repository):
        """Test that error responses are JSON serializable."""
        mock_repository.list.side_effect = RuntimeError("Test error")

        tool = SkillsListTool(repository=mock_repository)
        result = tool._run()

        # Should be able to parse error response
        response = json.loads(result)
        assert response["ok"] is False
        assert "RuntimeError" in response["content"]
