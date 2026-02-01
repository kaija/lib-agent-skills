"""Unit tests for data models."""

from datetime import datetime
from pathlib import Path

import pytest

from agent_skills.models import (
    AuditEvent,
    ExecutionPolicy,
    ExecutionResult,
    ResourcePolicy,
    SkillDescriptor,
    SkillSession,
    SkillState,
    ToolResponse,
)


class TestSkillDescriptor:
    """Tests for SkillDescriptor model."""
    
    def test_to_dict(self):
        """Test serialization to dict."""
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=Path("/path/to/skill"),
            license="MIT",
            hash="abc123",
            mtime=1234567890.0,
        )
        
        result = descriptor.to_dict()
        
        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill"
        assert result["path"] == "/path/to/skill"
        assert result["license"] == "MIT"
        assert result["hash"] == "abc123"
        assert result["mtime"] == 1234567890.0
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "name": "test-skill",
            "description": "A test skill",
            "path": "/path/to/skill",
            "license": "MIT",
            "compatibility": {"python": ">=3.10"},
            "metadata": {"version": "1.0.0"},
            "allowed_tools": ["skills.read"],
            "hash": "abc123",
            "mtime": 1234567890.0,
        }
        
        descriptor = SkillDescriptor.from_dict(data)
        
        assert descriptor.name == "test-skill"
        assert descriptor.description == "A test skill"
        assert descriptor.path == Path("/path/to/skill")
        assert descriptor.license == "MIT"
        assert descriptor.compatibility == {"python": ">=3.10"}
        assert descriptor.metadata == {"version": "1.0.0"}
        assert descriptor.allowed_tools == ["skills.read"]
        assert descriptor.hash == "abc123"
        assert descriptor.mtime == 1234567890.0
    
    def test_round_trip(self):
        """Test serialization round-trip."""
        original = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=Path("/path/to/skill"),
            license="MIT",
            compatibility={"python": ">=3.10"},
            metadata={"version": "1.0.0"},
            allowed_tools=["skills.read", "skills.run"],
            hash="abc123",
            mtime=1234567890.0,
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = SkillDescriptor.from_dict(data)
        
        # Verify all fields match
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.path == original.path
        assert restored.license == original.license
        assert restored.compatibility == original.compatibility
        assert restored.metadata == original.metadata
        assert restored.allowed_tools == original.allowed_tools
        assert restored.hash == original.hash
        assert restored.mtime == original.mtime


class TestExecutionResult:
    """Tests for ExecutionResult model."""
    
    def test_to_dict(self):
        """Test serialization to dict."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="",
            duration_ms=1234,
            meta={"sandbox": "local"},
        )
        
        data = result.to_dict()
        
        assert data["exit_code"] == 0
        assert data["stdout"] == "Success"
        assert data["stderr"] == ""
        assert data["duration_ms"] == 1234
        assert data["meta"] == {"sandbox": "local"}
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "exit_code": 1,
            "stdout": "Output",
            "stderr": "Error",
            "duration_ms": 5678,
            "meta": {"sandbox": "docker"},
        }
        
        result = ExecutionResult.from_dict(data)
        
        assert result.exit_code == 1
        assert result.stdout == "Output"
        assert result.stderr == "Error"
        assert result.duration_ms == 5678
        assert result.meta == {"sandbox": "docker"}
    
    def test_round_trip(self):
        """Test serialization round-trip."""
        original = ExecutionResult(
            exit_code=0,
            stdout="Success",
            stderr="Warning",
            duration_ms=1234,
            meta={"sandbox": "local", "cpu_time": 100},
        )
        
        data = original.to_dict()
        restored = ExecutionResult.from_dict(data)
        
        assert restored.exit_code == original.exit_code
        assert restored.stdout == original.stdout
        assert restored.stderr == original.stderr
        assert restored.duration_ms == original.duration_ms
        assert restored.meta == original.meta


class TestAuditEvent:
    """Tests for AuditEvent model."""
    
    def test_to_dict(self):
        """Test serialization to dict."""
        ts = datetime(2024, 1, 1, 12, 0, 0)
        event = AuditEvent(
            ts=ts,
            kind="read",
            skill="test-skill",
            path="references/api.md",
            bytes=1234,
            sha256="abc123",
            detail={"user": "test"},
        )
        
        data = event.to_dict()
        
        assert data["ts"] == "2024-01-01T12:00:00"
        assert data["kind"] == "read"
        assert data["skill"] == "test-skill"
        assert data["path"] == "references/api.md"
        assert data["bytes"] == 1234
        assert data["sha256"] == "abc123"
        assert data["detail"] == {"user": "test"}
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "ts": "2024-01-01T12:00:00",
            "kind": "run",
            "skill": "test-skill",
            "path": "scripts/process.py",
            "bytes": 5678,
            "sha256": "def456",
            "detail": {"exit_code": 0},
        }
        
        event = AuditEvent.from_dict(data)
        
        assert event.ts == datetime(2024, 1, 1, 12, 0, 0)
        assert event.kind == "run"
        assert event.skill == "test-skill"
        assert event.path == "scripts/process.py"
        assert event.bytes == 5678
        assert event.sha256 == "def456"
        assert event.detail == {"exit_code": 0}


class TestSkillSession:
    """Tests for SkillSession model."""
    
    def test_transition_valid(self):
        """Test valid state transitions."""
        session = SkillSession(
            session_id="test-123",
            skill_name="test-skill",
            state=SkillState.DISCOVERED,
        )
        
        # Valid transition
        session.transition(SkillState.SELECTED)
        assert session.state == SkillState.SELECTED
        
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        assert session.state == SkillState.INSTRUCTIONS_LOADED
        
        session.transition(SkillState.DONE)
        assert session.state == SkillState.DONE
    
    def test_transition_invalid(self):
        """Test invalid state transitions."""
        session = SkillSession(
            session_id="test-123",
            skill_name="test-skill",
            state=SkillState.DISCOVERED,
        )
        
        # Invalid transition (skip states)
        with pytest.raises(ValueError, match="Invalid state transition"):
            session.transition(SkillState.DONE)
    
    def test_add_artifact(self):
        """Test adding artifacts."""
        session = SkillSession(
            session_id="test-123",
            skill_name="test-skill",
            state=SkillState.DISCOVERED,
        )
        
        session.add_artifact("result", {"data": "value"})
        
        assert "result" in session.artifacts
        assert session.artifacts["result"] == {"data": "value"}
    
    def test_add_audit(self):
        """Test adding audit events."""
        session = SkillSession(
            session_id="test-123",
            skill_name="test-skill",
            state=SkillState.DISCOVERED,
        )
        
        event = AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill="test-skill",
        )
        
        session.add_audit(event)
        
        assert len(session.audit) == 1
        assert session.audit[0] == event
    
    def test_to_dict(self):
        """Test serialization to dict."""
        ts = datetime(2024, 1, 1, 12, 0, 0)
        session = SkillSession(
            session_id="test-123",
            skill_name="test-skill",
            state=SkillState.INSTRUCTIONS_LOADED,
            artifacts={"key": "value"},
            audit=[],
            created_at=ts,
            updated_at=ts,
        )
        
        data = session.to_dict()
        
        assert data["session_id"] == "test-123"
        assert data["skill_name"] == "test-skill"
        assert data["state"] == "instructions_loaded"
        assert data["artifacts"] == {"key": "value"}
        assert data["created_at"] == "2024-01-01T12:00:00"
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "session_id": "test-123",
            "skill_name": "test-skill",
            "state": "instructions_loaded",
            "artifacts": {"key": "value"},
            "audit": [],
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:00:00",
        }
        
        session = SkillSession.from_dict(data)
        
        assert session.session_id == "test-123"
        assert session.skill_name == "test-skill"
        assert session.state == SkillState.INSTRUCTIONS_LOADED
        assert session.artifacts == {"key": "value"}


class TestToolResponse:
    """Tests for ToolResponse model."""
    
    def test_to_dict_text_content(self):
        """Test serialization with text content."""
        response = ToolResponse(
            ok=True,
            type="instructions",
            skill="test-skill",
            path="SKILL.md",
            content="# Instructions",
            bytes=1234,
            sha256="abc123",
            truncated=False,
        )
        
        data = response.to_dict()
        
        assert data["ok"] is True
        assert data["type"] == "instructions"
        assert data["content"] == "# Instructions"
    
    def test_to_dict_binary_content(self):
        """Test serialization with binary content."""
        response = ToolResponse(
            ok=True,
            type="asset",
            skill="test-skill",
            path="assets/data.bin",
            content=b"binary data",
            bytes=11,
        )
        
        data = response.to_dict()
        
        # Binary content should be base64 encoded
        assert isinstance(data["content"], str)
        assert data["type"] == "asset"
    
    def test_to_dict_dict_content(self):
        """Test serialization with dict content."""
        response = ToolResponse(
            ok=True,
            type="execution_result",
            skill="test-skill",
            content={"exit_code": 0, "stdout": "Success"},
        )
        
        data = response.to_dict()
        
        assert data["content"] == {"exit_code": 0, "stdout": "Success"}


class TestResourcePolicy:
    """Tests for ResourcePolicy model."""
    
    def test_defaults(self):
        """Test default values."""
        policy = ResourcePolicy()
        
        assert policy.max_file_bytes == 200_000
        assert policy.max_total_bytes_per_session == 1_000_000
        assert ".md" in policy.allow_extensions_text
        assert policy.allow_binary_assets is False
        assert policy.binary_max_bytes == 2_000_000
    
    def test_to_dict(self):
        """Test serialization to dict."""
        policy = ResourcePolicy(
            max_file_bytes=100_000,
            allow_extensions_text={".txt", ".md"},
        )
        
        data = policy.to_dict()
        
        assert data["max_file_bytes"] == 100_000
        assert set(data["allow_extensions_text"]) == {".txt", ".md"}
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "max_file_bytes": 100_000,
            "allow_extensions_text": [".txt", ".md"],
            "allow_binary_assets": True,
        }
        
        policy = ResourcePolicy.from_dict(data)
        
        assert policy.max_file_bytes == 100_000
        assert policy.allow_extensions_text == {".txt", ".md"}
        assert policy.allow_binary_assets is True


class TestExecutionPolicy:
    """Tests for ExecutionPolicy model."""
    
    def test_defaults(self):
        """Test default values."""
        policy = ExecutionPolicy()
        
        assert policy.enabled is False
        assert len(policy.allow_skills) == 0
        assert len(policy.allow_scripts_glob) == 0
        assert policy.timeout_s_default == 60
        assert policy.network_access is False
        assert policy.workdir_mode == "skill_root"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"skill1", "skill2"},
            timeout_s_default=30,
        )
        
        data = policy.to_dict()
        
        assert data["enabled"] is True
        assert set(data["allow_skills"]) == {"skill1", "skill2"}
        assert data["timeout_s_default"] == 30
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "enabled": True,
            "allow_skills": ["skill1", "skill2"],
            "allow_scripts_glob": ["scripts/*.py"],
            "timeout_s_default": 30,
        }
        
        policy = ExecutionPolicy.from_dict(data)
        
        assert policy.enabled is True
        assert policy.allow_skills == {"skill1", "skill2"}
        assert policy.allow_scripts_glob == ["scripts/*.py"]
        assert policy.timeout_s_default == 30
