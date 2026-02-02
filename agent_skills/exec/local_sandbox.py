"""Local subprocess sandbox implementation.

This module provides a LocalSubprocessSandbox that executes scripts as
local subprocesses using Python's subprocess module. This is the default
sandbox provider for the Agent Skills Runtime.

Security Note:
    LocalSubprocessSandbox provides minimal isolation - scripts run as
    local processes with the same user permissions. For production use
    with untrusted scripts, consider using Docker or gVisor sandboxes.
"""

import subprocess
import time
from pathlib import Path

from agent_skills.exceptions import ScriptTimeoutError
from agent_skills.exec.sandbox import SandboxProvider
from agent_skills.models import ExecutionResult


class LocalSubprocessSandbox(SandboxProvider):
    """Execute scripts as local subprocesses.
    
    This sandbox implementation uses subprocess.run to execute scripts
    in the local environment. It provides:
    - Timeout enforcement via subprocess timeout parameter
    - Stdout/stderr capture
    - Execution duration measurement
    - Basic process isolation (separate process, not containerized)
    
    The sandbox does NOT provide:
    - Filesystem isolation
    - Network isolation
    - Resource limits (CPU, memory)
    - User/permission isolation
    
    For production use with untrusted scripts, use a more secure sandbox
    implementation (Docker, gVisor, etc.).
    
    Example:
        >>> sandbox = LocalSubprocessSandbox()
        >>> result = sandbox.execute(
        ...     script_path=Path("/path/to/script.py"),
        ...     args=["--input", "data.json"],
        ...     stdin=None,
        ...     timeout_s=30,
        ...     workdir=Path("/path/to/workdir"),
        ...     env={"PATH": "/usr/bin"},
        ... )
        >>> print(f"Exit code: {result.exit_code}")
        >>> print(f"Output: {result.stdout}")
    """
    
    def execute(
        self,
        script_path: Path,
        args: list[str],
        stdin: str | bytes | None,
        timeout_s: int,
        workdir: Path,
        env: dict[str, str],
    ) -> ExecutionResult:
        """Execute script as local subprocess.
        
        Args:
            script_path: Absolute path to the script file to execute
            args: Command-line arguments to pass to the script
            stdin: Optional standard input (string or bytes)
            timeout_s: Maximum execution time in seconds
            workdir: Working directory for script execution
            env: Environment variables for the script
            
        Returns:
            ExecutionResult containing exit code, stdout, stderr, duration,
            and metadata indicating this is a local subprocess execution
            
        Raises:
            ScriptTimeoutError: If script execution exceeds timeout_s
            
        Notes:
            - The script is executed directly (not in a shell)
            - stdout and stderr are captured and decoded as UTF-8
            - If decoding fails, replacement characters are used
            - The script path is used as-is (caller must ensure it's executable)
            - Duration is measured in milliseconds
        """
        # Prepare stdin input
        stdin_input = None
        if stdin is not None:
            if isinstance(stdin, str):
                stdin_input = stdin.encode("utf-8")
            else:
                stdin_input = stdin
        
        # Build command: [script_path, *args]
        # Note: We execute the script directly, not through a shell
        # The caller is responsible for ensuring the script is executable
        # (e.g., has shebang line, or is invoked via interpreter)
        cmd = [str(script_path)] + args
        
        # Measure execution time
        start_time = time.time()
        
        try:
            # Execute subprocess with timeout
            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                timeout=timeout_s,
                cwd=str(workdir),
                env=env,
                check=False,  # Don't raise exception on non-zero exit
            )
            
            # Calculate duration in milliseconds
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Decode stdout and stderr
            # Use 'replace' error handling to avoid decode errors
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            
            return ExecutionResult(
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                meta={"sandbox": "local_subprocess"},
            )
            
        except subprocess.TimeoutExpired as e:
            # Calculate duration up to timeout
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Try to decode any captured output before timeout
            stdout = ""
            stderr = ""
            if e.stdout:
                stdout = e.stdout.decode("utf-8", errors="replace")
            if e.stderr:
                stderr = e.stderr.decode("utf-8", errors="replace")
            
            # Raise timeout error with captured output in message
            raise ScriptTimeoutError(
                f"Script execution exceeded {timeout_s}s timeout. "
                f"Captured output - stdout: {stdout[:100]}..., stderr: {stderr[:100]}..."
            )
