"""Sandbox provider interface for script execution.

This module defines the abstract base class for script execution sandboxes.
Different sandbox implementations (local subprocess, Docker, gVisor, etc.)
can be plugged in by implementing the SandboxProvider interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from agent_skills.models import ExecutionResult


class SandboxProvider(ABC):
    """Abstract interface for script execution sandboxes.

    This interface defines the contract for executing scripts in isolated
    environments. Implementations should provide appropriate isolation
    mechanisms (subprocess, containers, VMs, etc.) based on security
    requirements.

    The sandbox is responsible for:
    - Executing the script with provided arguments
    - Capturing stdout and stderr
    - Enforcing timeout limits
    - Measuring execution duration
    - Providing execution metadata

    Example implementations:
    - LocalSubprocessSandbox: Execute as local subprocess
    - DockerSandbox: Execute in Docker container
    - gVisorSandbox: Execute with gVisor runtime
    """

    @abstractmethod
    def execute(
        self,
        script_path: Path,
        args: list[str],
        stdin: str | bytes | None,
        timeout_s: int,
        workdir: Path,
        env: dict[str, str],
    ) -> ExecutionResult:
        """Execute script in sandbox environment.

        Args:
            script_path: Absolute path to the script file to execute
            args: Command-line arguments to pass to the script
            stdin: Optional standard input (string or bytes)
            timeout_s: Maximum execution time in seconds
            workdir: Working directory for script execution
            env: Environment variables for the script

        Returns:
            ExecutionResult containing exit code, stdout, stderr, duration,
            and sandbox-specific metadata

        Raises:
            ScriptTimeoutError: If script execution exceeds timeout
            ScriptFailedError: If script execution fails (implementation-specific)

        Notes:
            - The sandbox should terminate the process if timeout is exceeded
            - stdout and stderr should be captured as strings (UTF-8 decoded)
            - duration_ms should measure actual execution time
            - meta dict should include sandbox-specific information
              (e.g., {"sandbox": "local_subprocess"})
        """
        pass
