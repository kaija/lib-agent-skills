"""Agent Skills Runtime - Lazy loading and progressive disclosure for Agent Skills.

This library provides a security-focused system for managing and executing Agent Skills
with support for LangChain and ADK frameworks, including autonomous agent capabilities.
"""

from agent_skills.exceptions import (
    AgentSkillsError,
    SkillNotFoundError,
    SkillParseError,
    PolicyViolationError,
    PathTraversalError,
    ResourceTooLargeError,
    ScriptExecutionDisabledError,
    ScriptTimeoutError,
    ScriptFailedError,
)

from agent_skills.models import (
    SkillDescriptor,
    SkillState,
    ExecutionResult,
    AuditEvent,
    SkillSession,
    ToolResponse,
    ResourcePolicy,
    ExecutionPolicy,
)

from agent_skills.observability import AuditSink, JSONLAuditSink, StdoutAuditSink
from agent_skills.runtime import SkillSessionManager, SkillsRepository
from agent_skills.agent import AutonomousAgent, ApprovalRequest, ApprovalResponse
from agent_skills.adapters import (
    build_asset_response,
    build_error_response,
    build_execution_response,
    build_instructions_response,
    build_metadata_response,
    build_reference_response,
    build_search_response,
    safe_tool_call,
)

__version__ = "0.1.0"

__all__ = [
    # Exceptions
    "AgentSkillsError",
    "SkillNotFoundError",
    "SkillParseError",
    "PolicyViolationError",
    "PathTraversalError",
    "ResourceTooLargeError",
    "ScriptExecutionDisabledError",
    "ScriptTimeoutError",
    "ScriptFailedError",
    # Models
    "SkillDescriptor",
    "SkillState",
    "ExecutionResult",
    "AuditEvent",
    "SkillSession",
    "ToolResponse",
    "ResourcePolicy",
    "ExecutionPolicy",
    # Runtime
    "SkillSessionManager",
    "SkillsRepository",
    # Autonomous Agent
    "AutonomousAgent",
    "ApprovalRequest",
    "ApprovalResponse",
    # Observability
    "AuditSink",
    "JSONLAuditSink",
    "StdoutAuditSink",
    # Tool Response Helpers
    "build_asset_response",
    "build_error_response",
    "build_execution_response",
    "build_instructions_response",
    "build_metadata_response",
    "build_reference_response",
    "build_search_response",
    "safe_tool_call",
]
