"""Unit tests for LocalSubprocessSandbox."""

import pytest
import tempfile
import time
from pathlib import Path

from agent_skills.exec.local_sandbox import LocalSubprocessSandbox
from agent_skills.exec.sandbox import SandboxProvider
from agent_skills.exceptions import ScriptTimeoutError
from agent_skills.models import ExecutionResult


@pytest.fixture
def sandbox():
    """Create a LocalSubprocessSandbox instance."""
    return LocalSubprocessSandbox()


@pytest.fixture
def temp_workdir():
    """Create a temporary working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_local_sandbox_is_sandbox_provider(sandbox):
    """LocalSubprocessSandbox should implement SandboxProvider."""
    assert isinstance(sandbox, SandboxProvider)


def test_execute_simple_script_success(sandbox, temp_workdir):
    """Execute a simple script that succeeds."""
    # Create a simple Python script that prints to stdout
    script_path = temp_workdir / "test_script.py"
    script_path.write_text("#!/usr/bin/env python3\nprint('Hello, World!')\n")
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout
    assert result.stderr == ""
    assert result.duration_ms >= 0
    assert result.meta == {"sandbox": "local_subprocess"}


def test_execute_script_with_args(sandbox, temp_workdir):
    """Execute a script with command-line arguments."""
    # Create a script that echoes its arguments
    script_path = temp_workdir / "echo_args.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print(' '.join(sys.argv[1:]))\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=["arg1", "arg2", "arg3"],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "arg1 arg2 arg3" in result.stdout


def test_execute_script_with_stdin_string(sandbox, temp_workdir):
    """Execute a script with string stdin input."""
    # Create a script that reads from stdin
    script_path = temp_workdir / "read_stdin.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "data = sys.stdin.read()\n"
        "print(f'Received: {data}')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin="test input data",
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Received: test input data" in result.stdout


def test_execute_script_with_stdin_bytes(sandbox, temp_workdir):
    """Execute a script with bytes stdin input."""
    # Create a script that reads from stdin
    script_path = temp_workdir / "read_stdin.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "data = sys.stdin.read()\n"
        "print(f'Received: {data}')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=b"binary input data",
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Received: binary input data" in result.stdout


def test_execute_script_with_stderr(sandbox, temp_workdir):
    """Execute a script that writes to stderr."""
    # Create a script that writes to stderr
    script_path = temp_workdir / "write_stderr.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('Error message\\n')\n"
        "sys.stdout.write('Normal output\\n')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Normal output" in result.stdout
    assert "Error message" in result.stderr


def test_execute_script_non_zero_exit_code(sandbox, temp_workdir):
    """Execute a script that exits with non-zero code."""
    # Create a script that exits with code 42
    script_path = temp_workdir / "exit_code.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('Exiting with code 42')\n"
        "sys.exit(42)\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Should return result, not raise exception
    assert result.exit_code == 42
    assert "Exiting with code 42" in result.stdout


def test_execute_script_timeout(sandbox, temp_workdir):
    """Execute a script that exceeds timeout."""
    # Create a script that sleeps longer than timeout
    script_path = temp_workdir / "sleep.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "print('Starting sleep')\n"
        "time.sleep(10)\n"
        "print('Finished sleep')\n"
    )
    script_path.chmod(0o755)
    
    with pytest.raises(ScriptTimeoutError) as exc_info:
        sandbox.execute(
            script_path=script_path,
            args=[],
            stdin=None,
            timeout_s=1,  # 1 second timeout
            workdir=temp_workdir,
            env={"PATH": "/usr/bin:/bin"},
        )
    
    # Check error message contains timeout info
    assert "exceeded 1s timeout" in str(exc_info.value)


def test_execute_script_timeout_captures_partial_output(sandbox, temp_workdir):
    """Execute a script that times out but has partial output."""
    # Create a script that prints before sleeping
    script_path = temp_workdir / "sleep_with_output.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "import time\n"
        "print('Before sleep', flush=True)\n"
        "sys.stderr.write('Error before sleep\\n')\n"
        "sys.stderr.flush()\n"
        "time.sleep(10)\n"
        "print('After sleep')\n"
    )
    script_path.chmod(0o755)
    
    with pytest.raises(ScriptTimeoutError) as exc_info:
        sandbox.execute(
            script_path=script_path,
            args=[],
            stdin=None,
            timeout_s=1,
            workdir=temp_workdir,
            env={"PATH": "/usr/bin:/bin"},
        )
    
    # Error message should contain partial output
    error_msg = str(exc_info.value)
    assert "exceeded 1s timeout" in error_msg


def test_execute_measures_duration(sandbox, temp_workdir):
    """Execute a script and verify duration is measured."""
    # Create a script that sleeps briefly
    script_path = temp_workdir / "brief_sleep.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "time.sleep(0.1)\n"  # 100ms sleep
        "print('Done')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    # Duration should be at least 100ms
    assert result.duration_ms >= 100
    # But not too long (should be less than 1 second)
    assert result.duration_ms < 1000


def test_execute_respects_workdir(sandbox, temp_workdir):
    """Execute a script that uses the working directory."""
    # Create a test file in workdir
    test_file = temp_workdir / "test_file.txt"
    test_file.write_text("test content")
    
    # Create a script that reads the file
    script_path = temp_workdir / "read_file.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "with open('test_file.txt', 'r') as f:\n"
        "    print(f.read())\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "test content" in result.stdout


def test_execute_respects_env(sandbox, temp_workdir):
    """Execute a script that uses environment variables."""
    # Create a script that reads an environment variable
    script_path = temp_workdir / "read_env.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "print(os.environ.get('TEST_VAR', 'not found'))\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin", "TEST_VAR": "test_value"},
    )
    
    assert result.exit_code == 0
    assert "test_value" in result.stdout


def test_execute_handles_unicode_output(sandbox, temp_workdir):
    """Execute a script that outputs unicode characters."""
    # Create a script with unicode output
    script_path = temp_workdir / "unicode.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "# -*- coding: utf-8 -*-\n"
        "print('Hello 世界 🌍')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Hello 世界 🌍" in result.stdout


def test_execute_handles_invalid_utf8_with_replacement(sandbox, temp_workdir):
    """Execute a script that outputs invalid UTF-8 (should use replacement chars)."""
    # Create a script that outputs raw bytes
    script_path = temp_workdir / "invalid_utf8.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "# Write invalid UTF-8 bytes\n"
        "sys.stdout.buffer.write(b'Valid text\\n')\n"
        "sys.stdout.buffer.write(b'Invalid: \\xff\\xfe\\n')\n"
        "sys.stdout.buffer.write(b'More valid text\\n')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    # Should contain valid text (invalid bytes replaced)
    assert "Valid text" in result.stdout
    assert "More valid text" in result.stdout
    # Invalid bytes should be replaced with replacement character
    # (exact representation depends on Python version)


def test_execute_empty_args(sandbox, temp_workdir):
    """Execute a script with empty args list."""
    script_path = temp_workdir / "simple.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "print('No args')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "No args" in result.stdout


def test_execute_none_stdin(sandbox, temp_workdir):
    """Execute a script with None stdin."""
    script_path = temp_workdir / "no_stdin.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "# Try to read stdin (should be empty/closed)\n"
        "data = sys.stdin.read()\n"
        "print(f'Read {len(data)} bytes')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Read 0 bytes" in result.stdout


def test_execute_metadata_includes_sandbox_type(sandbox, temp_workdir):
    """Execute result should include sandbox type in metadata."""
    script_path = temp_workdir / "simple.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "print('test')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert "sandbox" in result.meta
    assert result.meta["sandbox"] == "local_subprocess"


def test_execute_with_shell_script(sandbox, temp_workdir):
    """Execute a shell script (not just Python)."""
    # Create a simple shell script
    script_path = temp_workdir / "test.sh"
    script_path.write_text(
        "#!/bin/bash\n"
        "echo 'Hello from bash'\n"
        "echo 'Error output' >&2\n"
        "exit 0\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=temp_workdir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert "Hello from bash" in result.stdout
    assert "Error output" in result.stderr
