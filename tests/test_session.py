"""Unit tests for SkillSessionManager."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from agent_skills.models import AuditEvent, SkillSession, SkillState
from agent_skills.runtime.session import SkillSessionManager


class TestSkillSessionManager:
    """Tests for SkillSessionManager."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        return Mock()
    
    @pytest.fixture
    def manager(self, mock_repository):
        """Create a SkillSessionManager instance."""
        return SkillSessionManager(mock_repository)
    
    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create_session("test-skill")
        
        assert session.session_id is not None
        assert session.skill_name == "test-skill"
        assert session.state == SkillState.DISCOVERED
        assert len(session.artifacts) == 0
        assert len(session.audit) == 0
    
    def test_create_session_unique_ids(self, manager):
        """Test that each session gets a unique ID."""
        session1 = manager.create_session("skill1")
        session2 = manager.create_session("skill2")
        
        assert session1.session_id != session2.session_id
    
    def test_create_session_stores_in_registry(self, manager):
        """Test that created sessions are stored in the manager."""
        session = manager.create_session("test-skill")
        
        retrieved = manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    
    def test_get_session_existing(self, manager):
        """Test retrieving an existing session."""
        session = manager.create_session("test-skill")
        
        retrieved = manager.get_session(session.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.skill_name == "test-skill"
    
    def test_get_session_nonexistent(self, manager):
        """Test retrieving a non-existent session returns None."""
        result = manager.get_session("nonexistent-id")
        
        assert result is None
    
    def test_update_session(self, manager):
        """Test updating a session."""
        session = manager.create_session("test-skill")
        
        # Modify the session
        session.transition(SkillState.SELECTED)
        session.add_artifact("key", "value")
        
        # Update in manager
        manager.update_session(session)
        
        # Retrieve and verify
        retrieved = manager.get_session(session.session_id)
        assert retrieved.state == SkillState.SELECTED
        assert retrieved.artifacts["key"] == "value"
    
    def test_update_session_preserves_changes(self, manager):
        """Test that session updates are preserved."""
        session = manager.create_session("test-skill")
        original_id = session.session_id
        
        # Make multiple changes
        session.transition(SkillState.SELECTED)
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.add_artifact("artifact1", {"data": "value1"})
        session.add_artifact("artifact2", {"data": "value2"})
        
        event = AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill="test-skill",
        )
        session.add_audit(event)
        
        # Update
        manager.update_session(session)
        
        # Retrieve and verify all changes
        retrieved = manager.get_session(original_id)
        assert retrieved.state == SkillState.INSTRUCTIONS_LOADED
        assert len(retrieved.artifacts) == 2
        assert retrieved.artifacts["artifact1"] == {"data": "value1"}
        assert retrieved.artifacts["artifact2"] == {"data": "value2"}
        assert len(retrieved.audit) == 1
        assert retrieved.audit[0].kind == "activate"
    
    def test_list_sessions_empty(self, manager):
        """Test listing sessions when none exist."""
        sessions = manager.list_sessions()
        
        assert sessions == []
    
    def test_list_sessions_single(self, manager):
        """Test listing sessions with one session."""
        session = manager.create_session("test-skill")
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 1
        assert sessions[0].session_id == session.session_id
    
    def test_list_sessions_multiple(self, manager):
        """Test listing multiple sessions."""
        session1 = manager.create_session("skill1")
        session2 = manager.create_session("skill2")
        session3 = manager.create_session("skill3")
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 3
        session_ids = {s.session_id for s in sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids
    
    def test_delete_session_existing(self, manager):
        """Test deleting an existing session."""
        session = manager.create_session("test-skill")
        session_id = session.session_id
        
        result = manager.delete_session(session_id)
        
        assert result is True
        assert manager.get_session(session_id) is None
    
    def test_delete_session_nonexistent(self, manager):
        """Test deleting a non-existent session."""
        result = manager.delete_session("nonexistent-id")
        
        assert result is False
    
    def test_delete_session_removes_from_list(self, manager):
        """Test that deleted sessions are removed from the list."""
        session1 = manager.create_session("skill1")
        session2 = manager.create_session("skill2")
        
        manager.delete_session(session1.session_id)
        
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == session2.session_id
    
    def test_clear_sessions(self, manager):
        """Test clearing all sessions."""
        manager.create_session("skill1")
        manager.create_session("skill2")
        manager.create_session("skill3")
        
        manager.clear_sessions()
        
        sessions = manager.list_sessions()
        assert len(sessions) == 0
    
    def test_clear_sessions_empty(self, manager):
        """Test clearing sessions when none exist."""
        manager.clear_sessions()
        
        sessions = manager.list_sessions()
        assert len(sessions) == 0
    
    def test_session_workflow(self, manager):
        """Test a complete session workflow."""
        # Create session
        session = manager.create_session("data-processor")
        assert session.state == SkillState.DISCOVERED
        
        # Transition to SELECTED
        session.transition(SkillState.SELECTED)
        manager.update_session(session)
        
        # Transition to INSTRUCTIONS_LOADED
        session.transition(SkillState.INSTRUCTIONS_LOADED)
        session.add_artifact("instructions", "# How to use this skill")
        manager.update_session(session)
        
        # Add audit event
        event = AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill="data-processor",
            bytes=1234,
        )
        session.add_audit(event)
        manager.update_session(session)
        
        # Transition to RESOURCE_NEEDED
        session.transition(SkillState.RESOURCE_NEEDED)
        session.add_artifact("reference", "API documentation content")
        manager.update_session(session)
        
        # Transition to DONE
        session.transition(SkillState.DONE)
        manager.update_session(session)
        
        # Verify final state
        final_session = manager.get_session(session.session_id)
        assert final_session.state == SkillState.DONE
        assert len(final_session.artifacts) == 2
        assert len(final_session.audit) == 1
        
        # Clean up
        manager.delete_session(session.session_id)
        assert manager.get_session(session.session_id) is None
    
    def test_multiple_sessions_independent(self, manager):
        """Test that multiple sessions are independent."""
        session1 = manager.create_session("skill1")
        session2 = manager.create_session("skill2")
        
        # Modify session1
        session1.transition(SkillState.SELECTED)
        session1.add_artifact("key1", "value1")
        manager.update_session(session1)
        
        # Modify session2
        session2.transition(SkillState.SELECTED)
        session2.transition(SkillState.INSTRUCTIONS_LOADED)
        session2.add_artifact("key2", "value2")
        manager.update_session(session2)
        
        # Verify independence
        retrieved1 = manager.get_session(session1.session_id)
        retrieved2 = manager.get_session(session2.session_id)
        
        assert retrieved1.state == SkillState.SELECTED
        assert retrieved2.state == SkillState.INSTRUCTIONS_LOADED
        assert "key1" in retrieved1.artifacts
        assert "key1" not in retrieved2.artifacts
        assert "key2" in retrieved2.artifacts
        assert "key2" not in retrieved1.artifacts
    
    def test_repository_reference(self, mock_repository):
        """Test that manager maintains reference to repository."""
        manager = SkillSessionManager(mock_repository)
        
        assert manager.repository is mock_repository
