"""Unit tests for tool response helper functions."""

import hashlib
from pathlib import Path

import pytest

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
from agent_skills.exceptions import (
    PathTraversalError,
    PolicyViolationError,
    SkillNotFoundError,
)
from agent_skills.models import ExecutionResult, SkillDescriptor, ToolResponse


class TestBuildMetadataResponse:
    """Tests for build_metadata_response."""
    
    def test_build_metadata_response_single_skill(self):
        """Test building metadata response for a single skill."""
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=Path("/skills/test-skill"),
            hash="abc123",
            mtime=1234567890.0,
        )
        
        response = build_metadata_response("test-skill", [descriptor])
        
        assert response.ok is True
        assert response.type == "metadata"
        assert response.skill == "test-skill"
        assert response.path is None
        assert isinstance(response.content, list)
        assert len(response.content) == 1
        assert response.content[0]["name"] == "test-skill"
        assert response.content[0]["description"] == "A test skill"
        assert response.bytes is None
        assert response.sha256 is None
        assert response.truncated is False
        assert response.meta == {}
    
    def test_build_metadata_response_multiple_skills(self):
        """Test building metadata response for multiple skills."""
        descriptors = [
            SkillDescriptor(
                name="skill-1",
                description="First skill",
                path=Path("/skills/skill-1"),
            ),
            SkillDescriptor(
                name="skill-2",
                description="Second skill",
                path=Path("/skills/skill-2"),
            ),
        ]
        
        response = build_metadata_response("all", descriptors)
        
        assert response.ok is True
        assert response.type == "metadata"
        assert response.skill == "all"
        assert len(response.content) == 2
        assert response.content[0]["name"] == "skill-1"
        assert response.content[1]["name"] == "skill-2"
    
    def test_build_metadata_response_with_meta(self):
        """Test building metadata response with custom meta."""
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=Path("/skills/test-skill"),
        )
        
        response = build_metadata_response(
            "test-skill",
            [descriptor],
            meta={"filter": "active", "count": 1},
        )
        
        assert response.meta == {"filter": "active", "count": 1}
    
    def test_build_metadata_response_empty_list(self):
        """Test building metadata response with no skills."""
        response = build_metadata_response("all", [])
        
        assert response.ok is True
        assert response.type == "metadata"
        assert response.content == []


class TestBuildInstructionsResponse:
    """Tests for build_instructions_response."""
    
    def test_build_instructions_response(self):
        """Test building instructions response."""
        instructions = "# Test Skill\n\nThis is a test skill."
        
        response = build_instructions_response(
            "test-skill",
            instructions,
            "SKILL.md",
        )
        
        assert response.ok is True
        assert response.type == "instructions"
        assert response.skill == "test-skill"
        assert response.path == "SKILL.md"
        assert response.content == instructions
        assert response.bytes == len(instructions.encode("utf-8"))
        assert response.sha256 == hashlib.sha256(instructions.encode("utf-8")).hexdigest()
        assert response.truncated is False
    
    def test_build_instructions_response_empty(self):
        """Test building instructions response with empty content."""
        response = build_instructions_response(
            "test-skill",
            "",
            "SKILL.md",
        )
        
        assert response.ok is True
        assert response.content == ""
        assert response.bytes == 0
        assert response.sha256 == hashlib.sha256(b"").hexdigest()
    
    def test_build_instructions_response_with_meta(self):
        """Test building instructions response with custom meta."""
        response = build_instructions_response(
            "test-skill",
            "content",
            "SKILL.md",
            meta={"cached": True},
        )
        
        assert response.meta == {"cached": True}
    
    def test_build_instructions_response_unicode(self):
        """Test building instructions response with unicode content."""
        instructions = "# Test Skill\n\n🎉 Unicode content: 你好"
        
        response = build_instructions_response(
            "test-skill",
            instructions,
            "SKILL.md",
        )
        
        assert response.ok is True
        assert response.content == instructions
        assert response.bytes == len(instructions.encode("utf-8"))


class TestBuildReferenceResponse:
    """Tests for build_reference_response."""
    
    def test_build_reference_response(self):
        """Test building reference response."""
        content = "# API Documentation\n\nThis is the API docs."
        
        response = build_reference_response(
            "test-skill",
            "references/api-docs.md",
            content,
        )
        
        assert response.ok is True
        assert response.type == "reference"
        assert response.skill == "test-skill"
        assert response.path == "references/api-docs.md"
        assert response.content == content
        assert response.bytes == len(content.encode("utf-8"))
        assert response.sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert response.truncated is False
    
    def test_build_reference_response_truncated(self):
        """Test building reference response with truncation flag."""
        content = "Large file content..."
        
        response = build_reference_response(
            "test-skill",
            "references/large-file.md",
            content,
            truncated=True,
        )
        
        assert response.ok is True
        assert response.truncated is True
    
    def test_build_reference_response_with_meta(self):
        """Test building reference response with custom meta."""
        response = build_reference_response(
            "test-skill",
            "references/api-docs.md",
            "content",
            meta={"format": "markdown"},
        )
        
        assert response.meta == {"format": "markdown"}


class TestBuildAssetResponse:
    """Tests for build_asset_response."""
    
    def test_build_asset_response(self):
        """Test building asset response."""
        content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        
        response = build_asset_response(
            "test-skill",
            "assets/image.png",
            content,
        )
        
        assert response.ok is True
        assert response.type == "asset"
        assert response.skill == "test-skill"
        assert response.path == "assets/image.png"
        assert response.content == content
        assert response.bytes == len(content)
        assert response.sha256 == hashlib.sha256(content).hexdigest()
        assert response.truncated is False
    
    def test_build_asset_response_truncated(self):
        """Test building asset response with truncation flag."""
        content = b"binary data"
        
        response = build_asset_response(
            "test-skill",
            "assets/data.bin",
            content,
            truncated=True,
        )
        
        assert response.ok is True
        assert response.truncated is True
    
    def test_build_asset_response_empty(self):
        """Test building asset response with empty content."""
        content = b""
        
        response = build_asset_response(
            "test-skill",
            "assets/empty.bin",
            content,
        )
        
        assert response.ok is True
        assert response.content == b""
        assert response.bytes == 0


class TestBuildExecutionResponse:
    """Tests for build_execution_response."""
    
    def test_build_execution_response(self):
        """Test building execution response."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Processing complete\n",
            stderr="",
            duration_ms=1234,
            meta={"sandbox": "local_subprocess"},
        )
        
        response = build_execution_response(
            "test-skill",
            "scripts/process.py",
            result,
        )
        
        assert response.ok is True
        assert response.type == "execution_result"
        assert response.skill == "test-skill"
        assert response.path == "scripts/process.py"
        assert isinstance(response.content, dict)
        assert response.content["exit_code"] == 0
        assert response.content["stdout"] == "Processing complete\n"
        assert response.content["duration_ms"] == 1234
        assert response.bytes is None
        assert response.sha256 is None
        assert response.truncated is False
        assert "sandbox" in response.meta
    
    def test_build_execution_response_with_error(self):
        """Test building execution response for failed script."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error: File not found\n",
            duration_ms=100,
            meta={},
        )
        
        response = build_execution_response(
            "test-skill",
            "scripts/process.py",
            result,
        )
        
        assert response.ok is True  # Still ok=True, just non-zero exit code
        assert response.content["exit_code"] == 1
        assert response.content["stderr"] == "Error: File not found\n"
    
    def test_build_execution_response_meta_merge(self):
        """Test that execution response merges meta correctly."""
        result = ExecutionResult(
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100,
            meta={"sandbox": "local"},
        )
        
        response = build_execution_response(
            "test-skill",
            "scripts/test.py",
            result,
            meta={"custom": "value"},
        )
        
        assert response.meta["sandbox"] == "local"
        assert response.meta["custom"] == "value"


class TestBuildSearchResponse:
    """Tests for build_search_response."""
    
    def test_build_search_response(self):
        """Test building search response."""
        results = [
            {
                "path": "references/api-docs.md",
                "line_num": 42,
                "context": "...authentication token...",
            },
            {
                "path": "references/guide.md",
                "line_num": 15,
                "context": "...token validation...",
            },
        ]
        
        response = build_search_response(
            "test-skill",
            "token",
            results,
        )
        
        assert response.ok is True
        assert response.type == "search_results"
        assert response.skill == "test-skill"
        assert response.path is None
        assert response.content == results
        assert response.bytes is None
        assert response.sha256 is None
        assert response.truncated is False
        assert response.meta["query"] == "token"
        assert response.meta["result_count"] == 2
    
    def test_build_search_response_no_results(self):
        """Test building search response with no results."""
        response = build_search_response(
            "test-skill",
            "nonexistent",
            [],
        )
        
        assert response.ok is True
        assert response.content == []
        assert response.meta["result_count"] == 0
    
    def test_build_search_response_with_meta(self):
        """Test building search response with custom meta."""
        response = build_search_response(
            "test-skill",
            "query",
            [],
            meta={"max_results": 20},
        )
        
        assert response.meta["query"] == "query"
        assert response.meta["result_count"] == 0
        assert response.meta["max_results"] == 20


class TestBuildErrorResponse:
    """Tests for build_error_response."""
    
    def test_build_error_response_basic(self):
        """Test building basic error response."""
        error = SkillNotFoundError("Skill 'test-skill' not found")
        
        response = build_error_response("test-skill", error)
        
        assert response.ok is False
        assert response.type == "error"
        assert response.skill == "test-skill"
        assert response.path is None
        assert "SkillNotFoundError" in response.content
        assert "not found" in response.content
        assert response.bytes is None
        assert response.sha256 is None
        assert response.truncated is False
        assert response.meta["error_type"] == "SkillNotFoundError"
    
    def test_build_error_response_with_path(self):
        """Test building error response with path."""
        error = PathTraversalError("Path contains '..' component")
        
        response = build_error_response(
            "test-skill",
            error,
            path="../../etc/passwd",
        )
        
        assert response.ok is False
        assert response.path == "../../etc/passwd"
        assert response.meta["error_type"] == "PathTraversalError"
    
    def test_build_error_response_with_traceback(self):
        """Test building error response with traceback."""
        error = PolicyViolationError("Access denied")
        
        response = build_error_response(
            "test-skill",
            error,
            include_traceback=True,
        )
        
        assert response.ok is False
        assert "traceback" in response.meta
        assert isinstance(response.meta["traceback"], str)
    
    def test_build_error_response_generic_exception(self):
        """Test building error response from generic exception."""
        error = ValueError("Invalid input")
        
        response = build_error_response("test-skill", error)
        
        assert response.ok is False
        assert response.meta["error_type"] == "ValueError"
        assert "Invalid input" in response.content
    
    def test_build_error_response_exception_with_attributes(self):
        """Test building error response from exception with custom attributes."""
        error = PolicyViolationError("Policy violated")
        error.policy_name = "execution_policy"  # type: ignore
        error.violation_type = "skill_not_allowed"  # type: ignore
        
        response = build_error_response("test-skill", error)
        
        assert response.ok is False
        # Custom attributes should be in error_details if present
        # (depends on exception implementation)


class TestSafeToolCall:
    """Tests for safe_tool_call wrapper."""
    
    def test_safe_tool_call_success(self):
        """Test safe_tool_call with successful operation."""
        def operation():
            return build_instructions_response(
                "test-skill",
                "content",
                "SKILL.md",
            )
        
        response = safe_tool_call("test-skill", operation)
        
        assert response.ok is True
        assert response.type == "instructions"
    
    def test_safe_tool_call_with_exception(self):
        """Test safe_tool_call with exception."""
        def operation():
            raise SkillNotFoundError("Skill not found")
        
        response = safe_tool_call("test-skill", operation)
        
        assert response.ok is False
        assert response.type == "error"
        assert "SkillNotFoundError" in response.content
    
    def test_safe_tool_call_with_path(self):
        """Test safe_tool_call with path parameter."""
        def operation():
            raise PathTraversalError("Invalid path")
        
        response = safe_tool_call(
            "test-skill",
            operation,
            path="../../etc/passwd",
        )
        
        assert response.ok is False
        assert response.path == "../../etc/passwd"
    
    def test_safe_tool_call_with_traceback(self):
        """Test safe_tool_call with traceback enabled."""
        def operation():
            raise ValueError("Test error")
        
        response = safe_tool_call(
            "test-skill",
            operation,
            include_traceback=True,
        )
        
        assert response.ok is False
        assert "traceback" in response.meta
    
    def test_safe_tool_call_preserves_response(self):
        """Test that safe_tool_call preserves all response fields."""
        def operation():
            return build_metadata_response(
                "test-skill",
                [
                    SkillDescriptor(
                        name="test-skill",
                        description="Test",
                        path=Path("/test"),
                    )
                ],
                meta={"custom": "value"},
            )
        
        response = safe_tool_call("test-skill", operation)
        
        assert response.ok is True
        assert response.type == "metadata"
        assert response.meta["custom"] == "value"


class TestToolResponseSerialization:
    """Tests for ToolResponse serialization with helper functions."""
    
    def test_metadata_response_serialization(self):
        """Test that metadata response can be serialized."""
        descriptor = SkillDescriptor(
            name="test-skill",
            description="Test",
            path=Path("/test"),
        )
        response = build_metadata_response("test-skill", [descriptor])
        
        # Should be able to convert to dict
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["ok"] is True
        assert response_dict["type"] == "metadata"
    
    def test_instructions_response_serialization(self):
        """Test that instructions response can be serialized."""
        response = build_instructions_response(
            "test-skill",
            "content",
            "SKILL.md",
        )
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["content"] == "content"
    
    def test_asset_response_serialization(self):
        """Test that asset response with binary content can be serialized."""
        response = build_asset_response(
            "test-skill",
            "assets/data.bin",
            b"binary data",
        )
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        # Binary content should be base64 encoded
        assert isinstance(response_dict["content"], str)
    
    def test_execution_response_serialization(self):
        """Test that execution response can be serialized."""
        result = ExecutionResult(
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100,
            meta={},
        )
        response = build_execution_response(
            "test-skill",
            "scripts/test.py",
            result,
        )
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert isinstance(response_dict["content"], dict)
        assert response_dict["content"]["exit_code"] == 0
    
    def test_error_response_serialization(self):
        """Test that error response can be serialized."""
        error = SkillNotFoundError("Not found")
        response = build_error_response("test-skill", error)
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["ok"] is False
        assert isinstance(response_dict["content"], str)
