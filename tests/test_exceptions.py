"""Unit tests for exception classes."""

import pytest

from agent_skills.exceptions import (
    AgentSkillsError,
    PathTraversalError,
    PolicyViolationError,
    ResourceTooLargeError,
    ScriptExecutionDisabledError,
    ScriptFailedError,
    ScriptTimeoutError,
    SkillNotFoundError,
    SkillParseError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""
    
    def test_base_exception(self):
        """Test base exception can be raised."""
        with pytest.raises(AgentSkillsError):
            raise AgentSkillsError("Base error")
    
    def test_skill_not_found_error(self):
        """Test SkillNotFoundError is subclass of AgentSkillsError."""
        assert issubclass(SkillNotFoundError, AgentSkillsError)
        
        with pytest.raises(AgentSkillsError):
            raise SkillNotFoundError("Skill not found")
    
    def test_skill_parse_error(self):
        """Test SkillParseError is subclass of AgentSkillsError."""
        assert issubclass(SkillParseError, AgentSkillsError)
        
        with pytest.raises(AgentSkillsError):
            raise SkillParseError("Parse error")
    
    def test_policy_violation_error(self):
        """Test PolicyViolationError is subclass of AgentSkillsError."""
        assert issubclass(PolicyViolationError, AgentSkillsError)
        
        with pytest.raises(AgentSkillsError):
            raise PolicyViolationError("Policy violation")
    
    def test_path_traversal_error(self):
        """Test PathTraversalError is subclass of PolicyViolationError."""
        assert issubclass(PathTraversalError, PolicyViolationError)
        assert issubclass(PathTraversalError, AgentSkillsError)
        
        with pytest.raises(PolicyViolationError):
            raise PathTraversalError("Path traversal detected")
    
    def test_resource_too_large_error(self):
        """Test ResourceTooLargeError is subclass of PolicyViolationError."""
        assert issubclass(ResourceTooLargeError, PolicyViolationError)
        assert issubclass(ResourceTooLargeError, AgentSkillsError)
        
        with pytest.raises(PolicyViolationError):
            raise ResourceTooLargeError("Resource too large")
    
    def test_script_execution_disabled_error(self):
        """Test ScriptExecutionDisabledError is subclass of PolicyViolationError."""
        assert issubclass(ScriptExecutionDisabledError, PolicyViolationError)
        assert issubclass(ScriptExecutionDisabledError, AgentSkillsError)
        
        with pytest.raises(PolicyViolationError):
            raise ScriptExecutionDisabledError("Script execution disabled")
    
    def test_script_timeout_error(self):
        """Test ScriptTimeoutError is subclass of AgentSkillsError."""
        assert issubclass(ScriptTimeoutError, AgentSkillsError)
        
        with pytest.raises(AgentSkillsError):
            raise ScriptTimeoutError("Script timeout")
    
    def test_script_failed_error(self):
        """Test ScriptFailedError is subclass of AgentSkillsError."""
        assert issubclass(ScriptFailedError, AgentSkillsError)
        
        with pytest.raises(AgentSkillsError):
            raise ScriptFailedError("Script failed")
    
    def test_exception_messages(self):
        """Test exceptions preserve error messages."""
        message = "Custom error message"
        
        try:
            raise SkillNotFoundError(message)
        except SkillNotFoundError as e:
            assert str(e) == message
        
        try:
            raise PathTraversalError(message)
        except PathTraversalError as e:
            assert str(e) == message
