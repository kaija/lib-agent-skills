"""Integration tests for ScriptRunner with real sandbox."""

import pytest
import tempfile
from pathlib import Path

from agent_skills.exec.runner import ScriptRunner
from agent_skills.exec.local_sandbox import LocalSubprocessSandbox
from agent_skills.exceptions import (
    PathTraversalError,
    PolicyViolationError,
    ScriptExecutionDisabledError,
    ScriptTimeoutError,
)
from agent_skills.models import ExecutionPolicy


@pytest.fixture
def sandbox():
    """Create a real LocalSubprocessSandbox."""
    return LocalSubprocessSandbox()


@pytest.fixture
def temp_skill():
    """Create a temporary skill directory with various scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_root = Path(tmpdir)
        
        # Create scripts directory
        scripts_dir = skill_root / "scripts"
        scripts_dir.mkdir()
        
        # Create a simple Python script
        simple_script = scripts_dir / "simple.py"
        simple_script.write_text(
            "#!/usr/bin/env python3\n"
            "print('Hello from simple script')\n"
        )
        simple_script.chmod(0o755)
        
        # Create a script that uses arguments
        args_script = scripts_dir / "with_args.py"
        args_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "print(f'Args: {sys.argv[1:]}')\n"
        )
        args_script.chmod(0o755)
        
        # Create a script that reads stdin
        stdin_script = scripts_dir / "read_stdin.py"
        stdin_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "data = sys.stdin.read()\n"
            "print(f'Received: {data}')\n"
        )
        stdin_script.chmod(0o755)
        
        # Create a script that writes to stderr
        stderr_script = scripts_dir / "with_stderr.py"
        stderr_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "sys.stdout.write('stdout message\\n')\n"
            "sys.stderr.write('stderr message\\n')\n"
        )
        stderr_script.chmod(0o755)
        
        # Create a script that exits with non-zero code
        exit_script = scripts_dir / "exit_code.py"
        exit_script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "print('Exiting with code 5')\n"
            "sys.exit(5)\n"
        )
        exit_script.chmod(0o755)
        
        # Create a script that times out
        timeout_script = scripts_dir / "timeout.py"
        timeout_script.write_text(
            "#!/usr/bin/env python3\n"
            "import time\n"
            "print('Starting long operation')\n"
            "time.sleep(10)\n"
            "print('Finished')\n"
        )
        timeout_script.chmod(0o755)
        
        # Create a script in a subdirectory
        subdir = scripts_dir / "utils"
        subdir.mkdir()
        sub_script = subdir / "helper.py"
        sub_script.write_text(
            "#!/usr/bin/env python3\n"
            "print('Helper script')\n"
        )
        sub_script.chmod(0o755)
        
        # Create a shell script
        shell_script = scripts_dir / "test.sh"
        shell_script.write_text(
            "#!/bin/bash\n"
            "echo 'Hello from bash'\n"
        )
        shell_script.chmod(0o755)
        
        # Create references directory (for testing path restrictions)
        references_dir = skill_root / "references"
        references_dir.mkdir()
        bad_script = references_dir / "bad.py"
        bad_script.write_text(
            "#!/usr/bin/env python3\n"
            "print('This should not be executable')\n"
        )
        
        yield skill_root


def test_integration_simple_execution(sandbox, temp_skill):
    """Test simple script execution."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/simple.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "Hello from simple script" in result.stdout
    assert result.stderr == ""
    assert result.duration_ms > 0
    assert result.meta["sandbox"] == "local_subprocess"


def test_integration_script_with_arguments(sandbox, temp_skill):
    """Test script execution with arguments."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/with_args.py",
        args=["arg1", "arg2", "arg3"],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "['arg1', 'arg2', 'arg3']" in result.stdout


def test_integration_script_with_stdin(sandbox, temp_skill):
    """Test script execution with stdin."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/read_stdin.py",
        args=[],
        stdin="test input data",
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "Received: test input data" in result.stdout


def test_integration_script_with_stderr(sandbox, temp_skill):
    """Test script that writes to stderr."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/with_stderr.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "stdout message" in result.stdout
    assert "stderr message" in result.stderr


def test_integration_script_non_zero_exit(sandbox, temp_skill):
    """Test script that exits with non-zero code."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/exit_code.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    # Should return result, not raise exception
    assert result.exit_code == 5
    assert "Exiting with code 5" in result.stdout


def test_integration_script_timeout(sandbox, temp_skill):
    """Test script that exceeds timeout."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    with pytest.raises(ScriptTimeoutError):
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="scripts/timeout.py",
            args=[],
            stdin=None,
            timeout_s=1,  # Short timeout
        )


def test_integration_skill_allowlist_enforcement(sandbox, temp_skill):
    """Test skill allowlist is enforced."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"allowed-skill"},
    )
    runner = ScriptRunner(policy, sandbox)
    
    # Should fail for non-allowed skill
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill,
            skill_name="forbidden-skill",
            script_relpath="scripts/simple.py",
            args=[],
            stdin=None,
            timeout_s=5,
        )
    
    assert "not in execution allowlist" in str(exc_info.value).lower()


def test_integration_script_glob_enforcement(sandbox, temp_skill):
    """Test script glob patterns are enforced."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_scripts_glob=["scripts/*.sh"],  # Only shell scripts
    )
    runner = ScriptRunner(policy, sandbox)
    
    # Should fail for Python script
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="scripts/simple.py",
            args=[],
            stdin=None,
            timeout_s=5,
        )
    
    assert "does not match any allowed patterns" in str(exc_info.value).lower()
    
    # Should succeed for shell script
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/test.sh",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "Hello from bash" in result.stdout


def test_integration_path_traversal_prevention(sandbox, temp_skill):
    """Test path traversal is prevented."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    # Try to access file outside scripts directory
    with pytest.raises(PathTraversalError):
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="scripts/../references/bad.py",
            args=[],
            stdin=None,
            timeout_s=5,
        )


def test_integration_script_outside_scripts_dir(sandbox, temp_skill):
    """Test scripts outside scripts/ directory are rejected."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="references/bad.py",
            args=[],
            stdin=None,
            timeout_s=5,
        )
    
    assert "not in allowed directories" in str(exc_info.value).lower()


def test_integration_subdirectory_script(sandbox, temp_skill):
    """Test script in subdirectory can be executed."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_scripts_glob=["scripts/**/*.py"],
    )
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/utils/helper.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "Helper script" in result.stdout


def test_integration_execution_disabled(sandbox, temp_skill):
    """Test execution is disabled by default."""
    policy = ExecutionPolicy(enabled=False)
    runner = ScriptRunner(policy, sandbox)
    
    with pytest.raises(ScriptExecutionDisabledError):
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="scripts/simple.py",
            args=[],
            stdin=None,
            timeout_s=5,
        )


def test_integration_multiple_executions(sandbox, temp_skill):
    """Test multiple script executions in sequence."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, sandbox)
    
    # Execute first script
    result1 = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/simple.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result1.exit_code == 0
    
    # Execute second script
    result2 = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/with_args.py",
        args=["test"],
        stdin=None,
        timeout_s=5,
    )
    
    assert result2.exit_code == 0
    
    # Execute third script
    result3 = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/test.sh",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result3.exit_code == 0


def test_integration_complex_policy(sandbox, temp_skill):
    """Test complex policy with multiple constraints."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill", "other-skill"},
        allow_scripts_glob=["scripts/*.py", "scripts/utils/*.py"],
        timeout_s_default=30,
        env_allowlist={"PATH", "HOME"},
    )
    runner = ScriptRunner(policy, sandbox)
    
    # Should succeed for allowed skill and matching pattern
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/simple.py",
        args=[],
        stdin=None,
        timeout_s=None,  # Use default
    )
    
    assert result.exit_code == 0
    
    # Should fail for shell script (not in glob patterns)
    with pytest.raises(PolicyViolationError):
        runner.run(
            skill_root=temp_skill,
            skill_name="test-skill",
            script_relpath="scripts/test.sh",
            args=[],
            stdin=None,
            timeout_s=None,
        )
    
    # Should fail for non-allowed skill
    with pytest.raises(PolicyViolationError):
        runner.run(
            skill_root=temp_skill,
            skill_name="forbidden-skill",
            script_relpath="scripts/simple.py",
            args=[],
            stdin=None,
            timeout_s=None,
        )


def test_integration_shell_script_execution(sandbox, temp_skill):
    """Test shell script execution."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_scripts_glob=["scripts/*.sh"],
    )
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill,
        skill_name="test-skill",
        script_relpath="scripts/test.sh",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "Hello from bash" in result.stdout
