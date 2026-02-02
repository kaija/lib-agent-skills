"""Unit tests for SkillHandle."""

import pytest
from pathlib import Path
from datetime import datetime
from agent_skills.runtime.handle import SkillHandle
from agent_skills.models import (
    SkillDescriptor,
    ResourcePolicy,
    ExecutionPolicy,
    AuditEvent,
)
from agent_skills.observability.audit import AuditSink
from agent_skills.exceptions import (
    PathTraversalError,
    PolicyViolationError,
    ResourceTooLargeError,
    ScriptExecutionDisabledError,
)


class MockAuditSink(AuditSink):
    """Mock audit sink for testing."""
    
    def __init__(self):
        self.events = []
    
    def log(self, event: AuditEvent) -> None:
        self.events.append(event)
    
    def get_events_by_kind(self, kind: str) -> list[AuditEvent]:
        return [e for e in self.events if e.kind == kind]
    
    def clear(self):
        self.events.clear()


@pytest.fixture
def skill_directory(tmp_path):
    """Create a test skill directory structure."""
    skill_path = tmp_path / "test-skill"
    skill_path.mkdir()
    
    # Create SKILL.md with frontmatter and body
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill\n"
        "license: MIT\n"
        "---\n"
        "\n"
        "# Test Skill Instructions\n"
        "\n"
        "This is the skill body with instructions.\n"
        "Use this skill to test functionality.\n",
        encoding='utf-8'
    )
    
    # Create references directory with files
    refs_dir = skill_path / "references"
    refs_dir.mkdir()
    (refs_dir / "api-docs.md").write_text(
        "# API Documentation\n"
        "This is the API documentation.\n",
        encoding='utf-8'
    )
    (refs_dir / "guide.txt").write_text(
        "User Guide\n"
        "Follow these steps...\n",
        encoding='utf-8'
    )
    
    # Create subdirectory in references
    sub_refs = refs_dir / "examples"
    sub_refs.mkdir()
    (sub_refs / "example.json").write_text(
        '{"key": "value"}',
        encoding='utf-8'
    )
    
    # Create assets directory with files
    assets_dir = skill_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "data.bin").write_bytes(b"\x00\x01\x02\x03\x04")
    (assets_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    
    # Create scripts directory with scripts
    scripts_dir = skill_path / "scripts"
    scripts_dir.mkdir()
    
    # Create a simple Python script
    script_path = scripts_dir / "hello.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('Hello from script!')\n"
        "if len(sys.argv) > 1:\n"
        "    print(f'Args: {sys.argv[1:]}')\n"
        "if not sys.stdin.isatty():\n"
        "    stdin_data = sys.stdin.read()\n"
        "    if stdin_data:\n"
        "        print(f'Stdin: {stdin_data}')\n",
        encoding='utf-8'
    )
    script_path.chmod(0o755)
    
    # Create a script that exits with non-zero
    fail_script = scripts_dir / "fail.py"
    fail_script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('Error message', file=sys.stderr)\n"
        "sys.exit(1)\n",
        encoding='utf-8'
    )
    fail_script.chmod(0o755)
    
    # Create a script that times out
    timeout_script = scripts_dir / "timeout.py"
    timeout_script.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "time.sleep(10)\n",
        encoding='utf-8'
    )
    timeout_script.chmod(0o755)
    
    return skill_path


@pytest.fixture
def skill_descriptor(skill_directory):
    """Create a SkillDescriptor for the test skill."""
    return SkillDescriptor(
        name="test-skill",
        description="A test skill",
        path=skill_directory,
        license="MIT",
    )


@pytest.fixture
def default_resource_policy():
    """Create a default ResourcePolicy."""
    return ResourcePolicy()


@pytest.fixture
def permissive_execution_policy():
    """Create a permissive ExecutionPolicy for testing."""
    return ExecutionPolicy(
        enabled=True,
        allow_skills={"test-skill"},
        allow_scripts_glob=["scripts/*.py"],
        timeout_s_default=5,
    )


@pytest.fixture
def mock_audit_sink():
    """Create a mock audit sink."""
    return MockAuditSink()


class TestSkillHandleBasics:
    """Tests for basic SkillHandle functionality."""
    
    def test_create_handle(self, skill_descriptor, default_resource_policy):
        """Test creating a SkillHandle."""
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        assert handle is not None
        assert handle.descriptor() == skill_descriptor
    
    def test_descriptor_returns_correct_metadata(self, skill_descriptor, default_resource_policy):
        """Test that descriptor() returns the correct metadata."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        desc = handle.descriptor()
        assert desc.name == "test-skill"
        assert desc.description == "A test skill"
        assert desc.license == "MIT"


class TestSkillHandleInstructions:
    """Tests for instructions loading."""
    
    def test_load_instructions_first_time(
        self, skill_descriptor, default_resource_policy, mock_audit_sink
    ):
        """Test loading instructions for the first time."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        instructions = handle.instructions()
        
        assert "# Test Skill Instructions" in instructions
        assert "Use this skill to test functionality" in instructions
        
        # Check audit event was logged
        activate_events = mock_audit_sink.get_events_by_kind("activate")
        assert len(activate_events) == 1
        assert activate_events[0].skill == "test-skill"
        assert activate_events[0].path == "SKILL.md"
        assert activate_events[0].bytes > 0
        assert activate_events[0].sha256 is not None
    
    def test_load_instructions_cached(
        self, skill_descriptor, default_resource_policy, mock_audit_sink
    ):
        """Test that instructions are cached after first load."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        # Load instructions twice
        instructions1 = handle.instructions()
        instructions2 = handle.instructions()
        
        # Should return same content
        assert instructions1 == instructions2
        
        # Should only log one audit event (first load)
        activate_events = mock_audit_sink.get_events_by_kind("activate")
        assert len(activate_events) == 1
    
    def test_load_instructions_empty_body(self, tmp_path, default_resource_policy):
        """Test loading instructions when body is empty."""
        # Create skill with only frontmatter
        skill_path = tmp_path / "empty-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\n"
            "name: empty-skill\n"
            "description: Empty skill\n"
            "---\n",
            encoding='utf-8'
        )
        
        descriptor = SkillDescriptor(
            name="empty-skill",
            description="Empty skill",
            path=skill_path,
        )
        
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        instructions = handle.instructions()
        assert instructions == ""
    
    def test_load_instructions_without_audit_sink(
        self, skill_descriptor, default_resource_policy
    ):
        """Test loading instructions without audit sink."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=None,
        )
        
        # Should work without audit sink
        instructions = handle.instructions()
        assert "# Test Skill Instructions" in instructions


class TestSkillHandleReadReference:
    """Tests for reading reference files."""
    
    def test_read_reference_simple(
        self, skill_descriptor, default_resource_policy, mock_audit_sink
    ):
        """Test reading a simple reference file."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        content = handle.read_reference("api-docs.md")
        
        assert "# API Documentation" in content
        assert "This is the API documentation" in content
        
        # Check audit event
        read_events = mock_audit_sink.get_events_by_kind("read")
        assert len(read_events) == 1
        assert read_events[0].skill == "test-skill"
        assert read_events[0].path == "references/api-docs.md"
        assert read_events[0].bytes > 0
        assert read_events[0].sha256 is not None
    
    def test_read_reference_subdirectory(
        self, skill_descriptor, default_resource_policy
    ):
        """Test reading a reference file from subdirectory."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        content = handle.read_reference("examples/example.json")
        
        assert '{"key": "value"}' in content
    
    def test_read_reference_with_max_bytes(
        self, skill_descriptor, default_resource_policy
    ):
        """Test reading a reference file with max_bytes limit."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        # Read with very small limit
        content = handle.read_reference("api-docs.md", max_bytes=10)
        
        # Should be truncated
        assert len(content) <= 10
    
    def test_read_reference_nonexistent(
        self, skill_descriptor, default_resource_policy
    ):
        """Test reading a reference file that doesn't exist."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(FileNotFoundError):
            handle.read_reference("nonexistent.md")
    
    def test_read_reference_path_traversal(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that path traversal is prevented."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PathTraversalError):
            handle.read_reference("../outside.txt")
    
    def test_read_reference_absolute_path(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that absolute paths result in file not found (after prepending references/)."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        # When we prepend "references/" to "/etc/passwd", it becomes "references//etc/passwd"
        # which is no longer absolute, but it won't exist in the skill directory
        with pytest.raises(FileNotFoundError):
            handle.read_reference("/etc/passwd")
    
    def test_read_reference_directory(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that reading a directory is rejected."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PolicyViolationError):
            handle.read_reference("examples")


class TestSkillHandleReadAsset:
    """Tests for reading asset files."""
    
    def test_read_asset_simple(
        self, skill_descriptor, mock_audit_sink
    ):
        """Test reading a simple asset file."""
        # Enable binary assets
        resource_policy = ResourcePolicy(allow_binary_assets=True)
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        content = handle.read_asset("data.bin")
        
        assert content == b"\x00\x01\x02\x03\x04"
        
        # Check audit event
        read_events = mock_audit_sink.get_events_by_kind("read")
        assert len(read_events) == 1
        assert read_events[0].skill == "test-skill"
        assert read_events[0].path == "assets/data.bin"
        assert read_events[0].bytes == 5
    
    def test_read_asset_disabled(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that reading assets is disabled by default."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PolicyViolationError) as exc_info:
            handle.read_asset("data.bin")
        
        assert "Binary asset access is disabled" in str(exc_info.value)
    
    def test_read_asset_with_max_bytes(
        self, skill_descriptor
    ):
        """Test reading an asset with max_bytes limit."""
        resource_policy = ResourcePolicy(allow_binary_assets=True)
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
        )
        
        # Read with small limit
        content = handle.read_asset("image.png", max_bytes=10)
        
        # Should be truncated
        assert len(content) <= 10
    
    def test_read_asset_nonexistent(
        self, skill_descriptor
    ):
        """Test reading an asset that doesn't exist."""
        resource_policy = ResourcePolicy(allow_binary_assets=True)
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(FileNotFoundError):
            handle.read_asset("nonexistent.bin")
    
    def test_read_asset_path_traversal(
        self, skill_descriptor
    ):
        """Test that path traversal is prevented for assets."""
        resource_policy = ResourcePolicy(allow_binary_assets=True)
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PathTraversalError):
            handle.read_asset("../outside.bin")


class TestSkillHandleRunScript:
    """Tests for script execution."""
    
    def test_run_script_simple(
        self, skill_descriptor, default_resource_policy, 
        permissive_execution_policy, mock_audit_sink
    ):
        """Test running a simple script."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        result = handle.run_script("hello.py")
        
        assert result.exit_code == 0
        assert "Hello from script!" in result.stdout
        assert result.stderr == ""
        assert result.duration_ms > 0
        
        # Check audit event
        run_events = mock_audit_sink.get_events_by_kind("run")
        assert len(run_events) == 1
        assert run_events[0].skill == "test-skill"
        assert run_events[0].path == "scripts/hello.py"
        assert run_events[0].detail["exit_code"] == 0
    
    def test_run_script_with_args(
        self, skill_descriptor, default_resource_policy, permissive_execution_policy
    ):
        """Test running a script with arguments."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
        )
        
        result = handle.run_script("hello.py", args=["arg1", "arg2"])
        
        assert result.exit_code == 0
        assert "Args: ['arg1', 'arg2']" in result.stdout
    
    def test_run_script_with_stdin(
        self, skill_descriptor, default_resource_policy, permissive_execution_policy
    ):
        """Test running a script with stdin."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
        )
        
        result = handle.run_script("hello.py", stdin="test input")
        
        assert result.exit_code == 0
        assert "Stdin: test input" in result.stdout
    
    def test_run_script_non_zero_exit(
        self, skill_descriptor, default_resource_policy, permissive_execution_policy
    ):
        """Test running a script that exits with non-zero code."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
        )
        
        result = handle.run_script("fail.py")
        
        # Should return result, not raise exception
        assert result.exit_code == 1
        assert "Error message" in result.stderr
    
    def test_run_script_timeout(
        self, skill_descriptor, default_resource_policy, permissive_execution_policy
    ):
        """Test that script timeout is enforced."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
        )
        
        from agent_skills.exceptions import ScriptTimeoutError
        
        # Run with very short timeout
        with pytest.raises(ScriptTimeoutError):
            handle.run_script("timeout.py", timeout_s=1)
    
    def test_run_script_execution_disabled(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that script execution is disabled by default."""
        execution_policy = ExecutionPolicy(enabled=False)
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(ScriptExecutionDisabledError):
            handle.run_script("hello.py")
    
    def test_run_script_skill_not_in_allowlist(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that skill must be in allowlist."""
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"other-skill"},  # Not test-skill
        )
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PolicyViolationError) as exc_info:
            handle.run_script("hello.py")
        
        assert "not in execution allowlist" in str(exc_info.value)
    
    def test_run_script_not_matching_glob(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that script must match glob pattern."""
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"test-skill"},
            allow_scripts_glob=["scripts/*.sh"],  # Only .sh files
        )
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        with pytest.raises(PolicyViolationError) as exc_info:
            handle.run_script("hello.py")
        
        assert "does not match any allowed patterns" in str(exc_info.value)
    
    def test_run_script_path_traversal(
        self, skill_descriptor, default_resource_policy, permissive_execution_policy
    ):
        """Test that path traversal is prevented for scripts."""
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=permissive_execution_policy,
        )
        
        with pytest.raises(PathTraversalError):
            handle.run_script("../outside.py")
    
    def test_run_script_error_audit_event(
        self, skill_descriptor, default_resource_policy, mock_audit_sink
    ):
        """Test that errors are logged to audit sink."""
        execution_policy = ExecutionPolicy(enabled=False)
        
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=mock_audit_sink,
        )
        
        with pytest.raises(ScriptExecutionDisabledError):
            handle.run_script("hello.py")
        
        # Check error audit event
        error_events = mock_audit_sink.get_events_by_kind("error")
        assert len(error_events) == 1
        assert error_events[0].skill == "test-skill"
        assert error_events[0].path == "scripts/hello.py"
        assert "ScriptExecutionDisabledError" in error_events[0].detail["error_type"]


class TestSkillHandleSessionTracking:
    """Tests for session byte tracking across operations."""
    
    def test_session_bytes_tracked_across_reads(
        self, skill_descriptor, default_resource_policy
    ):
        """Test that session bytes are tracked across multiple reads."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        # Read multiple files
        handle.read_reference("api-docs.md")
        handle.read_reference("guide.txt")
        
        # Session bytes should be tracked in the resource reader
        assert handle._resource_reader.get_session_bytes_read() > 0
    
    def test_session_limit_enforced(
        self, tmp_path
    ):
        """Test that session byte limit is enforced."""
        # Create a skill with larger files
        skill_path = tmp_path / "limit-test"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\n"
            "name: limit-test\n"
            "description: Test skill\n"
            "---\n"
            "Body",
            encoding='utf-8'
        )
        
        # Create references directory with files
        refs_dir = skill_path / "references"
        refs_dir.mkdir()
        # Create files that are 100 bytes each
        (refs_dir / "file1.txt").write_text("X" * 100, encoding='utf-8')
        (refs_dir / "file2.txt").write_text("Y" * 100, encoding='utf-8')
        
        descriptor = SkillDescriptor(
            name="limit-test",
            description="Test skill",
            path=skill_path,
        )
        
        # Create policy with very low session limit
        resource_policy = ResourcePolicy(
            max_file_bytes=200,
            max_total_bytes_per_session=100,  # Can only read 1 file
        )
        execution_policy = ExecutionPolicy()
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
        )
        
        # First read should work and consume all 100 bytes
        content1 = handle.read_reference("file1.txt")
        assert len(content1) == 100
        
        # Second read should fail because we're already at the session limit
        with pytest.raises(ResourceTooLargeError):
            handle.read_reference("file2.txt")


class TestSkillHandleEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_handle_with_minimal_descriptor(self, tmp_path):
        """Test handle with minimal skill descriptor."""
        skill_path = tmp_path / "minimal"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\n"
            "name: minimal\n"
            "description: Minimal skill\n"
            "---\n"
            "Body",
            encoding='utf-8'
        )
        
        descriptor = SkillDescriptor(
            name="minimal",
            description="Minimal skill",
            path=skill_path,
        )
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=ResourcePolicy(),
            execution_policy=ExecutionPolicy(),
        )
        
        instructions = handle.instructions()
        assert instructions == "Body"
    
    def test_handle_without_audit_sink(self, skill_descriptor, default_resource_policy):
        """Test that handle works without audit sink."""
        execution_policy = ExecutionPolicy()
        handle = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
            audit_sink=None,
        )
        
        # All operations should work without audit sink
        instructions = handle.instructions()
        assert instructions is not None
        
        content = handle.read_reference("api-docs.md")
        assert content is not None
    
    def test_multiple_handles_same_skill(
        self, skill_descriptor, default_resource_policy
    ):
        """Test creating multiple handles for the same skill."""
        execution_policy = ExecutionPolicy()
        
        handle1 = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        handle2 = SkillHandle(
            descriptor=skill_descriptor,
            resource_policy=default_resource_policy,
            execution_policy=execution_policy,
        )
        
        # Both should work independently
        instructions1 = handle1.instructions()
        instructions2 = handle2.instructions()
        
        assert instructions1 == instructions2
        
        # Session bytes should be tracked separately
        handle1.read_reference("api-docs.md")
        handle2.read_reference("guide.txt")
        
        assert handle1._resource_reader.get_session_bytes_read() != \
               handle2._resource_reader.get_session_bytes_read()
