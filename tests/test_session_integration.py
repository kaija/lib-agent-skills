"""Integration tests for SkillSession and SkillSessionManager.

These tests verify the complete workflow of session management,
including state transitions, artifact storage, and audit trails.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from agent_skills.models import AuditEvent, SkillState
from agent_skills.runtime.session import SkillSessionManager


class TestSessionIntegration:
    """Integration tests for session management."""
    
    @pytest.fixture
    def manager(self):
        """Create a SkillSessionManager with mock repository."""
        mock_repo = Mock()
        return SkillSessionManager(mock_repo)
    
    def test_complete_skill_activation_workflow(self, manager):
        """Test a complete skill activation workflow with state transitions."""
        # Step 1: Create session for skill discovery
        session = manager.create_session("data-processor")
        assert session.state == SkillState.DISCOVERED
        
        # Step 2: Agent selects the skill
        session.transition(SkillState.SELECTED)
        manager.update_session(session)
        
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.SELECTED
        
        # Step 3: Load instructions
        instructions = "# Data Processor\n\nProcess CSV files..."
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.add_artifact("instructions", instructions)
        
        # Log activation event
        activation_event = AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill="data-processor",
            path="SKILL.md",
            bytes=len(instructions),
            sha256="abc123",
        )
        session.add_audit(activation_event)
        manager.update_session(session)
        
        # Verify state
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.INSTRUCTIONS_LOADED
        assert "instructions" in retrieved.artifacts
        assert len(retrieved.audit) == 1
        assert retrieved.audit[0].kind == "activate"
    
    def test_resource_access_workflow(self, manager):
        """Test workflow with resource access."""
        # Create and activate session
        session = manager.create_session("api-client")
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        
        # Agent needs to read reference documentation
        session.transition(SkillState.RESOURCE_NEEDED)
        
        # Read API documentation
        api_docs = "API Documentation content..."
        session.add_artifact("api_docs", api_docs)
        
        # Log read event
        read_event = AuditEvent(
            ts=datetime.now(),
            kind="read",
            skill="api-client",
            path="references/api-docs.md",
            bytes=len(api_docs),
            sha256="def456",
        )
        session.add_audit(read_event)
        manager.update_session(session)
        
        # Verify
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.RESOURCE_NEEDED
        assert "api_docs" in retrieved.artifacts
        assert len(retrieved.audit) == 1
        assert retrieved.audit[0].kind == "read"
    
    def test_script_execution_workflow(self, manager):
        """Test workflow with script execution."""
        # Create and prepare session
        session = manager.create_session("data-processor")
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.transition(SkillState.RESOURCE_NEEDED)
        
        # Agent needs to run a script
        session.transition(SkillState.SCRIPT_NEEDED)
        
        # Execute script
        execution_result = {
            "exit_code": 0,
            "stdout": "Processing complete\n",
            "stderr": "",
            "duration_ms": 1234,
        }
        session.add_artifact("execution_result", execution_result)
        
        # Log execution event
        run_event = AuditEvent(
            ts=datetime.now(),
            kind="run",
            skill="data-processor",
            path="scripts/process.py",
            detail={
                "args": ["--input", "data.csv"],
                "exit_code": 0,
                "duration_ms": 1234,
            },
        )
        session.add_audit(run_event)
        manager.update_session(session)
        
        # Verify
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.SCRIPT_NEEDED
        assert "execution_result" in retrieved.artifacts
        assert retrieved.artifacts["execution_result"]["exit_code"] == 0
        assert len(retrieved.audit) == 1
        assert retrieved.audit[0].kind == "run"
    
    def test_complete_workflow_to_done(self, manager):
        """Test complete workflow from discovery to done."""
        # Create session
        session = manager.create_session("data-processor")
        
        # Progress through states
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.add_artifact("instructions", "Instructions content")
        
        session.transition(SkillState.RESOURCE_NEEDED)
        session.add_artifact("reference", "Reference content")
        
        session.transition(SkillState.SCRIPT_NEEDED)
        session.add_artifact("execution_result", {"exit_code": 0})
        
        session.transition(SkillState.VERIFYING)
        session.add_artifact("verification", "All checks passed")
        
        session.transition(SkillState.DONE)
        manager.update_session(session)
        
        # Verify final state
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.DONE
        assert len(retrieved.artifacts) == 4
        assert "instructions" in retrieved.artifacts
        assert "reference" in retrieved.artifacts
        assert "execution_result" in retrieved.artifacts
        assert "verification" in retrieved.artifacts
    
    def test_workflow_with_failure(self, manager):
        """Test workflow that ends in failure."""
        # Create session
        session = manager.create_session("failing-skill")
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.transition(SkillState.SCRIPT_NEEDED)
        
        # Script execution fails
        execution_result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error: File not found\n",
            "duration_ms": 100,
        }
        session.add_artifact("execution_result", execution_result)
        
        # Log error event
        error_event = AuditEvent(
            ts=datetime.now(),
            kind="error",
            skill="failing-skill",
            path="scripts/process.py",
            detail={
                "error": "ScriptFailedError",
                "message": "Script exited with code 1",
            },
        )
        session.add_audit(error_event)
        
        # Transition to failed state
        session.transition(SkillState.FAILED)
        manager.update_session(session)
        
        # Verify
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.FAILED
        assert retrieved.artifacts["execution_result"]["exit_code"] == 1
        assert len(retrieved.audit) == 1
        assert retrieved.audit[0].kind == "error"
    
    def test_multiple_concurrent_sessions(self, manager):
        """Test managing multiple concurrent sessions."""
        # Create multiple sessions
        session1 = manager.create_session("skill1")
        session2 = manager.create_session("skill2")
        session3 = manager.create_session("skill3")
        
        # Progress each session independently
        session1.transition(SkillState.SELECTED)
        session1.transition(SkillState.INSTRUCTIONS_LOADED)
        session1.transition(SkillState.DONE)
        manager.update_session(session1)
        
        session2.transition(SkillState.SELECTED)
        session2.transition(SkillState.INSTRUCTIONS_LOADED)
        session2.transition(SkillState.RESOURCE_NEEDED)
        manager.update_session(session2)
        
        session3.transition(SkillState.SELECTED)
        session3.transition(SkillState.INSTRUCTIONS_LOADED)
        session3.transition(SkillState.FAILED)
        manager.update_session(session3)
        
        # Verify all sessions
        all_sessions = manager.list_sessions()
        assert len(all_sessions) == 3
        
        retrieved1 = manager.get_session(session1.session_id)
        retrieved2 = manager.get_session(session2.session_id)
        retrieved3 = manager.get_session(session3.session_id)
        
        assert retrieved1.state == SkillState.DONE
        assert retrieved2.state == SkillState.RESOURCE_NEEDED
        assert retrieved3.state == SkillState.FAILED
    
    def test_session_audit_trail_accumulation(self, manager):
        """Test that audit trail accumulates correctly."""
        session = manager.create_session("test-skill")
        
        # Add multiple audit events
        events = [
            AuditEvent(ts=datetime.now(), kind="activate", skill="test-skill"),
            AuditEvent(ts=datetime.now(), kind="read", skill="test-skill", path="ref.md"),
            AuditEvent(ts=datetime.now(), kind="read", skill="test-skill", path="api.md"),
            AuditEvent(ts=datetime.now(), kind="run", skill="test-skill", path="script.py"),
        ]
        
        for event in events:
            session.add_audit(event)
        
        manager.update_session(session)
        
        # Verify audit trail
        retrieved = manager.get_session(session.session_id)
        assert len(retrieved.audit) == 4
        assert retrieved.audit[0].kind == "activate"
        assert retrieved.audit[1].kind == "read"
        assert retrieved.audit[2].kind == "read"
        assert retrieved.audit[3].kind == "run"
    
    def test_session_cleanup_after_completion(self, manager):
        """Test cleaning up sessions after completion."""
        # Create and complete multiple sessions
        completed_sessions = []
        for i in range(3):
            session = manager.create_session(f"skill{i}")
            session.transition(SkillState.SELECTED)
            session.transition(SkillState.INSTRUCTIONS_LOADED)
            session.transition(SkillState.DONE)
            manager.update_session(session)
            completed_sessions.append(session.session_id)
        
        # Verify all sessions exist
        assert len(manager.list_sessions()) == 3
        
        # Clean up completed sessions
        for session_id in completed_sessions:
            manager.delete_session(session_id)
        
        # Verify all sessions are removed
        assert len(manager.list_sessions()) == 0
    
    def test_session_timestamps_update(self, manager):
        """Test that session timestamps are updated correctly."""
        session = manager.create_session("test-skill")
        created_at = session.created_at
        initial_updated_at = session.updated_at
        
        # Make a change
        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        session.transition(SkillState.SELECTED)
        
        # Verify updated_at changed but created_at didn't
        assert session.created_at == created_at
        assert session.updated_at > initial_updated_at
