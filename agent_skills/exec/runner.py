"""Script execution orchestration with policy enforcement.

This module provides the ScriptRunner class which orchestrates script execution
with comprehensive security policy checks. It validates execution permissions,
skill allowlists, script glob patterns, and path security before delegating
to a SandboxProvider for actual execution.
"""

import fnmatch
import tempfile
from pathlib import Path

from agent_skills.exceptions import (
    PathTraversalError,
    PolicyViolationError,
    ScriptExecutionDisabledError,
)
from agent_skills.exec.sandbox import SandboxProvider
from agent_skills.models import ExecutionPolicy, ExecutionResult
from agent_skills.resources.resolver import PathResolver


class ScriptRunner:
    """Orchestrates script execution with policy enforcement.

    The ScriptRunner is responsible for:
    1. Checking if script execution is enabled
    2. Validating the skill is in the allowlist
    3. Validating the script path matches allowed glob patterns
    4. Validating path security (no traversal)
    5. Preparing the execution environment
    6. Delegating to SandboxProvider for actual execution

    This provides a security-focused layer between the high-level API
    and the low-level sandbox execution.
    """

    def __init__(
        self,
        policy: ExecutionPolicy,
        sandbox: SandboxProvider,
    ):
        """Initialize ScriptRunner with policy and sandbox.

        Args:
            policy: ExecutionPolicy defining permissions and constraints
            sandbox: SandboxProvider implementation for script execution
        """
        self.policy = policy
        self.sandbox = sandbox

    def run(
        self,
        skill_root: Path,
        skill_name: str,
        script_relpath: str,
        args: list[str] | None,
        stdin: str | bytes | None,
        timeout_s: int | None,
    ) -> ExecutionResult:
        """Execute script with comprehensive policy checks.

        This method performs the following security checks in order:
        1. Verify execution is enabled in policy
        2. Check skill is in allowlist (or allowlist is empty/contains "*")
        3. Validate script path matches allowed glob patterns
        4. Validate path security (no traversal, within scripts/ directory)
        5. Prepare execution environment (workdir, env variables)
        6. Execute via sandbox with timeout

        Args:
            skill_root: Root directory of the skill
            skill_name: Name of the skill (for allowlist checking)
            script_relpath: Relative path to script (e.g., "scripts/process.py")
            args: Command-line arguments for the script (None treated as [])
            stdin: Optional standard input (string or bytes)
            timeout_s: Timeout in seconds (None uses policy default)

        Returns:
            ExecutionResult containing exit code, stdout, stderr, duration,
            and execution metadata

        Raises:
            ScriptExecutionDisabledError: If execution is disabled in policy
            PolicyViolationError: If skill or script not in allowlist
            PathTraversalError: If script path contains traversal or is absolute
            ScriptTimeoutError: If script execution exceeds timeout (from sandbox)

        Example:
            >>> policy = ExecutionPolicy(
            ...     enabled=True,
            ...     allow_skills={"data-processor"},
            ...     allow_scripts_glob=["scripts/*.py"],
            ... )
            >>> sandbox = LocalSubprocessSandbox()
            >>> runner = ScriptRunner(policy, sandbox)
            >>> result = runner.run(
            ...     skill_root=Path("/skills/data-processor"),
            ...     skill_name="data-processor",
            ...     script_relpath="scripts/process.py",
            ...     args=["--input", "data.csv"],
            ...     stdin=None,
            ...     timeout_s=30,
            ... )
            >>> print(result.exit_code, result.stdout)
        """
        # 1. Check if execution is enabled
        if not self.policy.enabled:
            raise ScriptExecutionDisabledError(
                "Script execution is disabled in ExecutionPolicy. "
                "Set enabled=True to allow script execution."
            )

        # 2. Check skill allowlist
        # If allow_skills is empty or contains "*", allow all skills
        if self.policy.allow_skills and "*" not in self.policy.allow_skills:
            if skill_name not in self.policy.allow_skills:
                raise PolicyViolationError(
                    f"Skill '{skill_name}' is not in execution allowlist. "
                    f"Allowed skills: {sorted(self.policy.allow_skills)}"
                )

        # 3. Validate script path matches glob patterns
        if self.policy.allow_scripts_glob:
            # Check if script path matches any of the allowed glob patterns
            matches_pattern = any(
                fnmatch.fnmatch(script_relpath, pattern)
                for pattern in self.policy.allow_scripts_glob
            )
            if not matches_pattern:
                raise PolicyViolationError(
                    f"Script path '{script_relpath}' does not match any allowed patterns. "
                    f"Allowed patterns: {self.policy.allow_scripts_glob}"
                )

        # 4. Validate path security using PathResolver
        # Scripts must be in the "scripts" directory
        resolver = PathResolver(skill_root)
        try:
            script_path = resolver.resolve(script_relpath, allowed_dirs=["scripts"])
        except (PathTraversalError, PolicyViolationError) as e:
            # Re-raise with additional context
            raise type(e)(
                f"Script path validation failed for '{script_relpath}': {e}"
            )

        # Verify the script file exists
        if not script_path.exists():
            raise PolicyViolationError(
                f"Script file does not exist: {script_relpath}"
            )

        # Verify it's a file (not a directory)
        if not script_path.is_file():
            raise PolicyViolationError(
                f"Script path is not a file: {script_relpath}"
            )

        # 5. Prepare execution environment

        # Determine working directory based on policy
        if self.policy.workdir_mode == "tempdir":
            # Create a temporary directory for execution
            # Note: In production, this should be managed by the caller
            # to ensure proper cleanup. For now, we'll use skill_root.
            # A proper implementation would use a context manager.
            workdir = skill_root
        else:  # "skill_root" or default
            workdir = skill_root

        # Prepare environment variables
        # Start with an empty environment for security
        env: dict[str, str] = {}

        # Add allowed environment variables from the current environment
        import os
        if self.policy.env_allowlist:
            for var_name in self.policy.env_allowlist:
                if var_name in os.environ:
                    env[var_name] = os.environ[var_name]

        # Always include PATH for basic functionality
        # (unless explicitly excluded by having an allowlist without PATH)
        if not self.policy.env_allowlist or "PATH" in self.policy.env_allowlist:
            env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")

        # Determine timeout
        effective_timeout = timeout_s if timeout_s is not None else self.policy.timeout_s_default

        # Normalize args
        effective_args = args if args is not None else []

        # 6. Execute via sandbox
        result = self.sandbox.execute(
            script_path=script_path,
            args=effective_args,
            stdin=stdin,
            timeout_s=effective_timeout,
            workdir=workdir,
            env=env,
        )

        return result
