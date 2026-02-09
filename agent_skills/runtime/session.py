"""Session management for Agent Skills Runtime.

This module provides SkillSessionManager for managing skill sessions,
particularly for ADK integration where sessions need to be maintained
across multiple tool calls.
"""

import uuid
from typing import TYPE_CHECKING

from agent_skills.models import SkillSession, SkillState

if TYPE_CHECKING:
    from agent_skills.runtime.repository import SkillsRepository


class SkillSessionManager:
    """Manages skill sessions for ADK integration.

    The SkillSessionManager maintains a registry of active SkillSession objects,
    allowing agents to create, retrieve, update, and list sessions. This is
    particularly useful for ADK integration where skill interactions span
    multiple tool calls and need to maintain state.

    Attributes:
        repository: The SkillsRepository instance
        _sessions: Internal dictionary mapping session_id to SkillSession
    """

    def __init__(self, repository: "SkillsRepository"):
        """Initialize with repository.

        Args:
            repository: The SkillsRepository instance to use for skill access
        """
        self.repository = repository
        self._sessions: dict[str, SkillSession] = {}

    def create_session(self, skill_name: str) -> SkillSession:
        """Create new session for skill.

        Creates a new SkillSession with a unique session ID and initial state
        of DISCOVERED. The session is automatically stored in the manager's
        internal registry.

        Args:
            skill_name: Name of the skill to create a session for

        Returns:
            The newly created SkillSession

        Example:
            >>> manager = SkillSessionManager(repository)
            >>> session = manager.create_session("data-processor")
            >>> print(session.state)
            SkillState.DISCOVERED
        """
        session_id = str(uuid.uuid4())
        session = SkillSession(
            session_id=session_id,
            skill_name=skill_name,
            state=SkillState.DISCOVERED,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SkillSession | None:
        """Retrieve existing session.

        Args:
            session_id: The unique identifier of the session to retrieve

        Returns:
            The SkillSession if found, None otherwise

        Example:
            >>> session = manager.get_session("abc-123")
            >>> if session:
            ...     print(f"Found session for {session.skill_name}")
        """
        return self._sessions.get(session_id)

    def update_session(self, session: SkillSession) -> None:
        """Persist session updates.

        Updates the stored session with the provided session object. This is
        typically called after modifying a session's state, artifacts, or
        audit trail.

        Args:
            session: The SkillSession to update

        Example:
            >>> session = manager.get_session("abc-123")
            >>> session.transition(SkillState.INSTRUCTIONS_LOADED)
            >>> manager.update_session(session)
        """
        self._sessions[session.session_id] = session

    def list_sessions(self) -> list[SkillSession]:
        """List all active sessions.

        Returns:
            List of all SkillSession objects currently managed

        Example:
            >>> sessions = manager.list_sessions()
            >>> for session in sessions:
            ...     print(f"{session.skill_name}: {session.state.value}")
        """
        return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Removes a session from the manager's registry. This is useful for
        cleaning up completed or failed sessions.

        Args:
            session_id: The unique identifier of the session to delete

        Returns:
            True if the session was found and deleted, False otherwise

        Example:
            >>> if manager.delete_session("abc-123"):
            ...     print("Session deleted")
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def clear_sessions(self) -> None:
        """Clear all sessions.

        Removes all sessions from the manager's registry. This is useful for
        testing or resetting the manager state.

        Example:
            >>> manager.clear_sessions()
            >>> assert len(manager.list_sessions()) == 0
        """
        self._sessions.clear()
