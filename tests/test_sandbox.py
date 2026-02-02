"""Unit tests for SandboxProvider interface."""

import pytest
from pathlib import Path
from abc import ABC

from agent_skills.exec.sandbox import SandboxProvider
from agent_skills.models import ExecutionResult


def test_sandbox_provider_is_abstract():
    """SandboxProvider should be an abstract base class."""
    assert issubclass(SandboxProvider, ABC)


def test_sandbox_provider_cannot_be_instantiated():
    """SandboxProvider cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SandboxProvider()


def test_sandbox_provider_has_execute_method():
    """SandboxProvider should define execute abstract method."""
    assert hasattr(SandboxProvider, "execute")
    assert callable(getattr(SandboxProvider, "execute"))


def test_sandbox_provider_execute_signature():
    """SandboxProvider.execute should have correct signature."""
    import inspect
    
    sig = inspect.signature(SandboxProvider.execute)
    params = list(sig.parameters.keys())
    
    # Check required parameters
    assert "self" in params
    assert "script_path" in params
    assert "args" in params
    assert "stdin" in params
    assert "timeout_s" in params
    assert "workdir" in params
    assert "env" in params


def test_concrete_sandbox_implementation():
    """A concrete implementation should be able to implement SandboxProvider."""
    
    class TestSandbox(SandboxProvider):
        """Test implementation of SandboxProvider."""
        
        def execute(
            self,
            script_path: Path,
            args: list[str],
            stdin: str | bytes | None,
            timeout_s: int,
            workdir: Path,
            env: dict[str, str],
        ) -> ExecutionResult:
            """Test implementation."""
            return ExecutionResult(
                exit_code=0,
                stdout="test output",
                stderr="",
                duration_ms=100,
                meta={"sandbox": "test"}
            )
    
    # Should be able to instantiate concrete implementation
    sandbox = TestSandbox()
    assert isinstance(sandbox, SandboxProvider)
    
    # Should be able to call execute
    result = sandbox.execute(
        script_path=Path("/test/script.py"),
        args=["--arg1", "value1"],
        stdin=None,
        timeout_s=60,
        workdir=Path("/test"),
        env={"PATH": "/usr/bin"},
    )
    
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert result.stdout == "test output"
    assert result.stderr == ""
    assert result.duration_ms == 100
    assert result.meta == {"sandbox": "test"}


def test_incomplete_implementation_fails():
    """A class that doesn't implement execute should fail to instantiate."""
    
    class IncompleteSandbox(SandboxProvider):
        """Incomplete implementation missing execute method."""
        pass
    
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteSandbox()
