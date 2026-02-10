"""Autonomous agent implementation.

This module provides an autonomous agent that handles the complete workflow
from user question to task completion, including skill selection, resource
loading, and script execution with user approval.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Any
from pathlib import Path
import json

from agent_skills.runtime import SkillsRepository
from agent_skills.models import ExecutionPolicy


@dataclass
class ApprovalRequest:
    """Request for user approval to execute a script.

    This contains all information the user needs to make an informed decision
    about whether to approve the script execution.
    """
    skill_name: str
    script_path: str
    args: list[str]
    stdin: Optional[str]
    timeout_s: int

    # Context information
    skill_description: str
    script_full_path: str
    working_directory: str

    # What the agent is trying to accomplish
    task_description: str
    reasoning: str

    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            "skill_name": self.skill_name,
            "script_path": self.script_path,
            "args": self.args,
            "stdin": self.stdin,
            "timeout_s": self.timeout_s,
            "skill_description": self.skill_description,
            "script_full_path": self.script_full_path,
            "working_directory": self.working_directory,
            "task_description": self.task_description,
            "reasoning": self.reasoning,
        }


@dataclass
class ApprovalResponse:
    """User's response to an approval request."""
    approved: bool
    reason: Optional[str] = None  # Optional reason for rejection


class AutonomousAgent:
    """Autonomous agent that handles complete task execution.

    This agent:
    1. Takes a user question
    2. Uses LLM to select appropriate skills
    3. Loads skill instructions and references
    4. Executes scripts (with user approval via callback)
    5. Iterates until task completion

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>>
        >>> def approval_callback(request: ApprovalRequest) -> ApprovalResponse:
        ...     print(f"Approve execution of {request.script_path}?")
        ...     print(f"Reasoning: {request.reasoning}")
        ...     response = input("Approve? (y/n): ")
        ...     return ApprovalResponse(approved=response.lower() == 'y')
        >>>
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> agent = AutonomousAgent(
        ...     repository=repo,
        ...     llm=llm,
        ...     approval_callback=approval_callback,
        ... )
        >>>
        >>> result = agent.run("Convert sample.csv to JSON format")
    """

    def __init__(
        self,
        repository: SkillsRepository,
        llm: Any,  # LangChain LLM or compatible
        approval_callback: Optional[Callable[[ApprovalRequest], ApprovalResponse]] = None,
        max_iterations: int = 15,
        verbose: bool = True,
    ):
        """Initialize autonomous agent.

        Args:
            repository: SkillsRepository with discovered skills
            llm: LLM instance (LangChain ChatOpenAI or compatible)
            approval_callback: Optional callback for script execution approval.
                             If None, all executions are auto-approved.
            max_iterations: Maximum number of agent iterations
            verbose: Whether to print progress information
        """
        self.repository = repository
        self.llm = llm
        self.approval_callback = approval_callback
        self.max_iterations = max_iterations
        self.verbose = verbose

        # Build tools from repository
        self._build_tools()

    def _build_tools(self):
        """Build internal tools for agent operations."""
        # Import here to avoid circular dependencies
        from agent_skills.adapters.langchain import build_langchain_tools

        self.tools = build_langchain_tools(self.repository)
        self.tools_by_name = {tool.name: tool for tool in self.tools}

        if self.verbose:
            print(f"[Agent] Built {len(self.tools)} tools:")
            print(f"  • skills_list - List available skills")
            print(f"  • skills_activate - Load skill instructions")
            print(f"  • skills_read - Read references/assets")
            print(f"  • skills_run - Execute scripts")
            print(f"  • skills_search - Search references")
            print(f"  • skills_check_file - Check file existence")
            print(f"  • skills_write_file - Write files")
            print(f"  • skills_delete_file - Delete files")

    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _create_system_prompt(self) -> str:
        """Create system prompt with available skills."""
        skills_info = self.repository.to_prompt(format="json")

        return f"""You are an autonomous AI agent with access to specialized skills and file operations.

AVAILABLE SKILLS:
{skills_info}

AVAILABLE TOOLS:
- skills_list: List all available skills (with optional query filter)
- skills_activate: Load skill instructions from SKILL.md
- skills_read: Read files from skill's references/ or assets/ directories
- skills_run: Execute scripts from skill's scripts/ directory (NOT for shell commands)
- skills_search: Search for text in skill's references/
- skills_check_file: Check if a file exists and get its properties
- skills_write_file: Write content to a file (with validation and overwrite protection)
- skills_delete_file: Delete a file (requires confirm=true)

IMPORTANT TOOL USAGE RULES:
- skills_run is ONLY for executing scripts from a skill's scripts/ directory
- DO NOT use skills_run for shell commands like rm, mkdir, cp, etc.
- Use skills_write_file to create files, not shell commands
- Use skills_delete_file to remove files (requires confirm=true)
- Use skills_check_file to verify files, not shell commands

WORKFLOW:
1. Analyze the user's question/task
2. Use skills_list to find relevant skills (you can filter by query)
3. Use skills_activate to load the skill's instructions
4. Use skills_read to access documentation and references as needed
5. Use skills_check_file to verify input files exist before processing
6. Use skills_write_file to create configuration files, schemas, or other needed files
7. Use skills_run to execute scripts when necessary
8. Use skills_check_file to verify output files were created successfully
9. Use skills_delete_file to clean up temporary or unwanted files (with confirm=true)
10. Iterate until the task is complete
11. Provide a clear final answer to the user

FILE OPERATIONS:
- Use skills_check_file before reading files to ensure they exist
- Use skills_write_file to create files (JSON, text, configs, schemas)
- Use skills_delete_file to remove files (requires confirm=true for safety)
- JSON files are automatically validated before writing
- Files are not overwritten by default (use overwrite=true if needed)
- Maximum file size is 10MB

IMPORTANT RULES:
- Always activate a skill before using it (to understand how it works)
- Read references/documentation when you need more information
- Check if input files exist before processing
- Create necessary files (schemas, configs) using skills_write_file
- When executing scripts, provide clear reasoning for why you need to run them
- If a script fails, analyze the error and try alternative approaches
- Verify outputs were created successfully using skills_check_file
- When deleting files, always set confirm=true to confirm the deletion
- Provide helpful, detailed responses to the user

Remember: You have full autonomy to select skills, read documentation, create files,
delete files, and execute scripts to accomplish the user's task. Use your judgment to
determine the best approach.
"""

    def _request_approval(
        self,
        skill_name: str,
        script_path: str,
        args: list[str],
        stdin: Optional[str],
        timeout_s: int,
        task_description: str,
        reasoning: str,
    ) -> ApprovalResponse:
        """Request user approval for script execution.

        Args:
            skill_name: Name of the skill
            script_path: Path to the script
            args: Script arguments
            stdin: Standard input
            timeout_s: Timeout in seconds
            task_description: What the agent is trying to accomplish
            reasoning: Why the agent wants to execute this script

        Returns:
            ApprovalResponse with user's decision
        """
        # Get skill information
        try:
            handle = self.repository.open(skill_name)
            descriptor = handle._descriptor
            skill_description = descriptor.description
            script_full_path = str(descriptor.path / "scripts" / script_path)
            working_directory = str(descriptor.path)
        except Exception:
            # If skill not found (e.g., 'system'), use generic info
            skill_description = f"System skill: {skill_name}"
            script_full_path = script_path
            working_directory = "."

        # Create approval request
        request = ApprovalRequest(
            skill_name=skill_name,
            script_path=script_path,
            args=args,
            stdin=stdin,
            timeout_s=timeout_s,
            skill_description=skill_description,
            script_full_path=script_full_path,
            working_directory=working_directory,
            task_description=task_description,
            reasoning=reasoning,
        )

        # If no callback, auto-approve
        if self.approval_callback is None:
            self._log(f"[Agent] Auto-approving execution: {script_path}")
            return ApprovalResponse(approved=True)

        # Call user's approval callback
        return self.approval_callback(request)

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool and return the result.

        For skills_run, this will request user approval before execution.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool execution result as string
        """
        tool = self.tools_by_name.get(tool_name)
        if tool is None:
            return json.dumps({
                "ok": False,
                "error": f"Tool '{tool_name}' not found"
            })

        # Special handling for skills_run - request approval
        if tool_name == "skills_run":
            # Extract execution parameters
            skill_name = tool_args.get("name", "")
            script_path = tool_args.get("script_path", "")
            args = tool_args.get("args", [])
            stdin = tool_args.get("stdin")
            timeout_s = tool_args.get("timeout_s", 30)

            # Request approval
            approval = self._request_approval(
                skill_name=skill_name,
                script_path=script_path,
                args=args,
                stdin=stdin,
                timeout_s=timeout_s,
                task_description=self.current_task,
                reasoning="Agent determined this script execution is necessary to complete the task",
            )

            if not approval.approved:
                self._log(f"[Agent] Execution rejected by user: {approval.reason}")
                return json.dumps({
                    "ok": False,
                    "error": f"Execution rejected by user: {approval.reason or 'No reason provided'}"
                })

            self._log(f"[Agent] Execution approved by user")

        # Execute the tool
        try:
            result = tool.invoke(tool_args)
            return result
        except Exception as e:
            return json.dumps({
                "ok": False,
                "error": str(e)
            })

    def run(self, task: str) -> str:
        """Run the autonomous agent to complete a task.

        Args:
            task: User's question or task description

        Returns:
            Final answer from the agent

        Example:
            >>> result = agent.run("Convert sample.csv to JSON format")
            >>> print(result)
        """
        self.current_task = task

        self._log("=" * 70)
        self._log(f"[Agent] Starting autonomous execution")
        self._log(f"[Agent] Task: {task}")
        self._log("=" * 70)

        # Import LangChain components
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
        except ImportError:
            raise ImportError(
                "LangChain is required for autonomous agent. "
                "Install with: pip install langchain-core"
            )

        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(self.tools)

        # Create initial messages
        system_msg = SystemMessage(content=self._create_system_prompt())
        user_msg = HumanMessage(content=task)
        messages = [system_msg, user_msg]

        # Agent loop
        for iteration in range(self.max_iterations):
            self._log(f"\n[Iteration {iteration + 1}]")

            # Get LLM response
            try:
                ai_msg = llm_with_tools.invoke(messages)
                messages.append(ai_msg)
            except Exception as e:
                self._log(f"[Agent] Error invoking LLM: {e}")
                return f"Error: Failed to get LLM response: {e}"

            # Check if there are tool calls
            if not ai_msg.tool_calls:
                # No more tool calls, we have the final answer
                self._log(f"[Agent] Task completed")
                final_answer = ai_msg.content

                self._log("=" * 70)
                self._log("[Agent] Final Answer:")
                self._log("=" * 70)
                self._log(final_answer)
                self._log("=" * 70)

                return final_answer

            # Execute tool calls
            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                self._log(f"  → Calling: {tool_name}")

                # Log args (truncate if too long)
                args_str = str(tool_args)
                if len(args_str) > 100:
                    args_str = args_str[:100] + "..."
                self._log(f"    Args: {args_str}")

                # Execute tool
                result = self._execute_tool(tool_name, tool_args)

                # Add tool result to messages
                tool_msg = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
                messages.append(tool_msg)

                # Log result (truncate if too long)
                result_str = str(result)
                if len(result_str) > 200:
                    result_str = result_str[:200] + "..."
                self._log(f"    Result: {result_str}")

        # Max iterations reached
        self._log(f"[Agent] Max iterations ({self.max_iterations}) reached")
        return f"Task incomplete: Maximum iterations ({self.max_iterations}) reached. Please try again with a more specific task or increase max_iterations."
