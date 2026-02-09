"""Autonomous agent module for agent-skills library.

This module provides a high-level autonomous agent that can:
1. Accept a user question
2. Select appropriate skills
3. Load instructions and references
4. Execute scripts (with user approval)
5. Iterate until task completion

The user only needs to provide:
- The question/task
- An LLM instance
- An approval callback (optional)
"""

from agent_skills.agent.autonomous import AutonomousAgent, ApprovalRequest, ApprovalResponse

__all__ = ["AutonomousAgent", "ApprovalRequest", "ApprovalResponse"]
