"""Exception classes for Agent Skills Runtime."""


class AgentSkillsError(Exception):
    """Base exception for all agent-skills errors."""
    pass


class SkillNotFoundError(AgentSkillsError):
    """Raised when a requested skill does not exist."""
    pass


class SkillParseError(AgentSkillsError):
    """Raised when SKILL.md parsing fails."""
    pass


class PolicyViolationError(AgentSkillsError):
    """Raised when an operation violates security policy."""
    pass


class PathTraversalError(PolicyViolationError):
    """Raised when path traversal is attempted."""
    pass


class ResourceTooLargeError(PolicyViolationError):
    """Raised when resource size limits are exceeded."""
    pass


class ScriptExecutionDisabledError(PolicyViolationError):
    """Raised when script execution is disabled."""
    pass


class ScriptTimeoutError(AgentSkillsError):
    """Raised when script execution exceeds timeout."""
    pass


class ScriptFailedError(AgentSkillsError):
    """Raised when script execution fails."""
    pass
