"""Unit tests for ScriptRunner."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from agent_skills.exec.runner import ScriptRunner
from agent_skills.exec.sandbox import SandboxProvider
from agent_skills.exceptions import (
    PathTraversalError,
    PolicyViolationError,
    ScriptExecutionDisabledError,
)
from agent_skills.models import ExecutionPolicy, ExecutionResult


@pytest.fixture
def mock_sandbox():
    """Create a mock SandboxProvider."""
    sandbox = Mock(spec=SandboxProvider)
    # Default successful execution
    sandbox.execute.return_value = ExecutionResult(
        exit_code=0,
        stdout="test output",
        stderr="",
        duration_ms=100,
        meta={"sandbox": "mock"},
    )
    return sandbox


@pytest.fixture
def temp_skill_root():
    """Create a temporary skill directory with scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_root = Path(tmpdir)
        
        # Create scripts directory
        scripts_dir = skill_root / "scripts"
        scripts_dir.mkdir()
        
        # Create a test script
        test_script = scripts_dir / "test.py"
        test_script.write_text("#!/usr/bin/env python3\nprint('test')\n")
        test_script.chmod(0o755)
        
        # Create another script
        process_script = scripts_dir / "process.py"
        process_script.write_text("#!/usr/bin/env python3\nprint('processing')\n")
        process_script.chmod(0o755)
        
        # Create a shell script
        shell_script = scripts_dir / "run.sh"
        shell_script.write_text("#!/bin/bash\necho 'running'\n")
        shell_script.chmod(0o755)
        
        yield skill_root


def test_runner_execution_disabled_by_default(mock_sandbox, temp_skill_root):
    """ScriptRunner should raise error when execution is disabled."""
    policy = ExecutionPolicy(enabled=False)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(ScriptExecutionDisabledError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="scripts/test.py",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "execution is disabled" in str(exc_info.value).lower()
    # Sandbox should not be called
    mock_sandbox.execute.assert_not_called()


def test_runner_skill_not_in_allowlist(mock_sandbox, temp_skill_root):
    """ScriptRunner should raise error when skill not in allowlist."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"allowed-skill", "another-skill"},
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="forbidden-skill",
            script_relpath="scripts/test.py",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "not in execution allowlist" in str(exc_info.value).lower()
    assert "forbidden-skill" in str(exc_info.value)
    mock_sandbox.execute.assert_not_called()


def test_runner_skill_in_allowlist_succeeds(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow execution when skill is in allowlist."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill", "other-skill"},
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_empty_allowlist_allows_all_skills(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow all skills when allowlist is empty."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills=set(),  # Empty allowlist
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="any-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_wildcard_allows_all_skills(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow all skills when allowlist contains '*'."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"*"},
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="any-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_script_not_matching_glob_pattern(mock_sandbox, temp_skill_root):
    """ScriptRunner should raise error when script doesn't match glob patterns."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.sh"],  # Only shell scripts
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="scripts/test.py",  # Python script, not allowed
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "does not match any allowed patterns" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_script_matching_glob_pattern_succeeds(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow execution when script matches glob pattern."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.py"],
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_multiple_glob_patterns(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow scripts matching any glob pattern."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.py", "scripts/*.sh"],
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    # Test Python script
    result1 = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    assert result1.exit_code == 0
    
    # Test shell script
    result2 = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/run.sh",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    assert result2.exit_code == 0


def test_runner_empty_glob_list_allows_all_scripts(mock_sandbox, temp_skill_root):
    """ScriptRunner should allow all scripts when glob list is empty."""
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=[],  # Empty list
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_path_traversal_with_dotdot(mock_sandbox, temp_skill_root):
    """ScriptRunner should reject paths with .. components."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PathTraversalError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="scripts/../etc/passwd",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "traversal" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_absolute_path_rejected(mock_sandbox, temp_skill_root):
    """ScriptRunner should reject absolute paths."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PathTraversalError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="/etc/passwd",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "absolute" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_script_not_in_scripts_directory(mock_sandbox, temp_skill_root):
    """ScriptRunner should reject scripts not in scripts/ directory."""
    # Create a script in references directory
    references_dir = temp_skill_root / "references"
    references_dir.mkdir()
    bad_script = references_dir / "bad.py"
    bad_script.write_text("#!/usr/bin/env python3\nprint('bad')\n")
    
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="references/bad.py",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "not in allowed directories" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_nonexistent_script(mock_sandbox, temp_skill_root):
    """ScriptRunner should raise error for nonexistent scripts."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="scripts/nonexistent.py",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "does not exist" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_script_is_directory(mock_sandbox, temp_skill_root):
    """ScriptRunner should raise error if script path is a directory."""
    # Create a subdirectory in scripts
    subdir = temp_skill_root / "scripts" / "subdir"
    subdir.mkdir()
    
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    with pytest.raises(PolicyViolationError) as exc_info:
        runner.run(
            skill_root=temp_skill_root,
            skill_name="test-skill",
            script_relpath="scripts/subdir",
            args=[],
            stdin=None,
            timeout_s=10,
        )
    
    assert "not a file" in str(exc_info.value).lower()
    mock_sandbox.execute.assert_not_called()


def test_runner_passes_args_to_sandbox(mock_sandbox, temp_skill_root):
    """ScriptRunner should pass arguments to sandbox."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    args = ["--input", "data.csv", "--output", "result.json"]
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=args,
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["args"] == args


def test_runner_passes_stdin_to_sandbox(mock_sandbox, temp_skill_root):
    """ScriptRunner should pass stdin to sandbox."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    stdin_data = "test input data"
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=stdin_data,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["stdin"] == stdin_data


def test_runner_uses_default_timeout_when_none(mock_sandbox, temp_skill_root):
    """ScriptRunner should use policy default timeout when None provided."""
    policy = ExecutionPolicy(enabled=True, timeout_s_default=42)
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=None,  # Use default
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["timeout_s"] == 42


def test_runner_uses_provided_timeout(mock_sandbox, temp_skill_root):
    """ScriptRunner should use provided timeout over default."""
    policy = ExecutionPolicy(enabled=True, timeout_s_default=42)
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,  # Override default
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["timeout_s"] == 10


def test_runner_workdir_is_skill_root(mock_sandbox, temp_skill_root):
    """ScriptRunner should use skill root as working directory."""
    policy = ExecutionPolicy(enabled=True, workdir_mode="skill_root")
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["workdir"] == temp_skill_root


def test_runner_env_includes_path_by_default(mock_sandbox, temp_skill_root):
    """ScriptRunner should include PATH in environment by default."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    env = call_args.kwargs["env"]
    assert "PATH" in env


def test_runner_env_respects_allowlist(mock_sandbox, temp_skill_root):
    """ScriptRunner should only include allowed environment variables."""
    import os
    
    # Set some test environment variables
    os.environ["TEST_VAR_1"] = "value1"
    os.environ["TEST_VAR_2"] = "value2"
    os.environ["TEST_VAR_3"] = "value3"
    
    policy = ExecutionPolicy(
        enabled=True,
        env_allowlist={"TEST_VAR_1", "TEST_VAR_3", "PATH"},
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    env = call_args.kwargs["env"]
    
    # Should include allowed vars
    assert "TEST_VAR_1" in env
    assert "TEST_VAR_3" in env
    assert "PATH" in env
    
    # Should not include disallowed var
    assert "TEST_VAR_2" not in env
    
    # Cleanup
    del os.environ["TEST_VAR_1"]
    del os.environ["TEST_VAR_2"]
    del os.environ["TEST_VAR_3"]


def test_runner_env_empty_when_no_allowlist(mock_sandbox, temp_skill_root):
    """ScriptRunner should have minimal env when allowlist is empty."""
    policy = ExecutionPolicy(
        enabled=True,
        env_allowlist=set(),  # Empty allowlist
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    env = call_args.kwargs["env"]
    
    # Should still have PATH for basic functionality
    assert "PATH" in env


def test_runner_none_args_converted_to_empty_list(mock_sandbox, temp_skill_root):
    """ScriptRunner should convert None args to empty list."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=None,
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    assert call_args.kwargs["args"] == []


def test_runner_returns_sandbox_result(mock_sandbox, temp_skill_root):
    """ScriptRunner should return the result from sandbox."""
    expected_result = ExecutionResult(
        exit_code=42,
        stdout="custom output",
        stderr="custom error",
        duration_ms=500,
        meta={"custom": "metadata"},
    )
    mock_sandbox.execute.return_value = expected_result
    
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result == expected_result
    assert result.exit_code == 42
    assert result.stdout == "custom output"
    assert result.stderr == "custom error"
    assert result.duration_ms == 500
    assert result.meta == {"custom": "metadata"}


def test_runner_passes_correct_script_path_to_sandbox(mock_sandbox, temp_skill_root):
    """ScriptRunner should pass resolved absolute path to sandbox."""
    policy = ExecutionPolicy(enabled=True)
    runner = ScriptRunner(policy, mock_sandbox)
    
    runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    call_args = mock_sandbox.execute.call_args
    script_path = call_args.kwargs["script_path"]
    
    # Should be absolute path
    assert script_path.is_absolute()
    # Should point to the test.py file
    assert script_path.name == "test.py"
    # Should be within skill root (resolve both paths to handle symlinks)
    assert script_path.resolve().is_relative_to(temp_skill_root.resolve())


def test_runner_glob_pattern_with_subdirectories(mock_sandbox, temp_skill_root):
    """ScriptRunner should handle glob patterns with subdirectories."""
    # Create a subdirectory with a script
    subdir = temp_skill_root / "scripts" / "utils"
    subdir.mkdir()
    sub_script = subdir / "helper.py"
    sub_script.write_text("#!/usr/bin/env python3\nprint('helper')\n")
    
    policy = ExecutionPolicy(
        enabled=True,
        allow_scripts_glob=["scripts/**/*.py"],  # Recursive pattern
    )
    runner = ScriptRunner(policy, mock_sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/utils/helper.py",
        args=[],
        stdin=None,
        timeout_s=10,
    )
    
    assert result.exit_code == 0
    mock_sandbox.execute.assert_called_once()


def test_runner_integration_with_real_sandbox(temp_skill_root):
    """Integration test with real LocalSubprocessSandbox."""
    from agent_skills.exec.local_sandbox import LocalSubprocessSandbox
    
    policy = ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.py"],
        timeout_s_default=5,
    )
    sandbox = LocalSubprocessSandbox()
    runner = ScriptRunner(policy, sandbox)
    
    result = runner.run(
        skill_root=temp_skill_root,
        skill_name="test-skill",
        script_relpath="scripts/test.py",
        args=[],
        stdin=None,
        timeout_s=5,
    )
    
    assert result.exit_code == 0
    assert "test" in result.stdout
    assert result.duration_ms >= 0
    assert result.meta["sandbox"] == "local_subprocess"
