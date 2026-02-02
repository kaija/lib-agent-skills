"""Integration tests for SkillHandle.

These tests verify the complete workflow of using SkillHandle with all components
working together: lazy loading, resource access, script execution, and audit logging.
"""

import pytest
from pathlib import Path
from agent_skills.runtime.handle import SkillHandle
from agent_skills.models import (
    SkillDescriptor,
    ResourcePolicy,
    ExecutionPolicy,
)
from agent_skills.observability.audit import JSONLAuditSink
import json


@pytest.fixture
def complete_skill(tmp_path):
    """Create a complete skill with all components."""
    skill_path = tmp_path / "complete-skill"
    skill_path.mkdir()
    
    # Create SKILL.md
    (skill_path / "SKILL.md").write_text(
        "---\n"
        "name: complete-skill\n"
        "description: A complete test skill\n"
        "license: MIT\n"
        "metadata:\n"
        "  version: 1.0.0\n"
        "  author: Test Author\n"
        "---\n"
        "\n"
        "# Complete Skill\n"
        "\n"
        "This skill demonstrates all features:\n"
        "- Reading references\n"
        "- Reading assets\n"
        "- Running scripts\n"
        "- Audit logging\n",
        encoding='utf-8'
    )
    
    # Create references
    refs_dir = skill_path / "references"
    refs_dir.mkdir()
    (refs_dir / "guide.md").write_text(
        "# User Guide\n"
        "Follow these steps to use the skill.\n",
        encoding='utf-8'
    )
    (refs_dir / "api.json").write_text(
        '{"endpoints": ["/api/v1/data", "/api/v1/process"]}',
        encoding='utf-8'
    )
    
    # Create assets
    assets_dir = skill_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "config.bin").write_bytes(b"\x00\x01\x02\x03")
    
    # Create scripts
    scripts_dir = skill_path / "scripts"
    scripts_dir.mkdir()
    
    # Create a data processing script
    process_script = scripts_dir / "process.py"
    process_script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "import json\n"
        "\n"
        "# Read input from stdin\n"
        "if not sys.stdin.isatty():\n"
        "    data = sys.stdin.read()\n"
        "    try:\n"
        "        parsed = json.loads(data)\n"
        "        print(f'Processed {len(parsed)} items')\n"
        "        sys.exit(0)\n"
        "    except json.JSONDecodeError as e:\n"
        "        print(f'Error: {e}', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "else:\n"
        "    print('No input provided', file=sys.stderr)\n"
        "    sys.exit(1)\n",
        encoding='utf-8'
    )
    process_script.chmod(0o755)
    
    return skill_path


@pytest.fixture
def audit_log_path(tmp_path):
    """Create a path for audit log."""
    return tmp_path / "audit.jsonl"


class TestSkillHandleCompleteWorkflow:
    """Test complete workflow with all features."""
    
    def test_complete_workflow(self, complete_skill, audit_log_path):
        """Test a complete workflow using all SkillHandle features."""
        # Create descriptor
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        # Create policies
        resource_policy = ResourcePolicy(
            allow_binary_assets=True,
        )
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"complete-skill"},
            allow_scripts_glob=["scripts/*.py"],
        )
        
        # Create audit sink
        audit_sink = JSONLAuditSink(audit_log_path)
        
        # Create handle
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
            audit_sink=audit_sink,
        )
        
        # Step 1: Load instructions (lazy loaded)
        instructions = handle.instructions()
        assert "# Complete Skill" in instructions
        assert "This skill demonstrates all features" in instructions
        
        # Step 2: Read a reference file
        guide = handle.read_reference("guide.md")
        assert "# User Guide" in guide
        
        # Step 3: Read another reference (JSON)
        api_spec = handle.read_reference("api.json")
        assert "/api/v1/data" in api_spec
        
        # Step 4: Read a binary asset
        config = handle.read_asset("config.bin")
        assert config == b"\x00\x01\x02\x03"
        
        # Step 5: Run a script with input
        input_data = '["item1", "item2", "item3"]'
        result = handle.run_script("process.py", stdin=input_data)
        assert result.exit_code == 0
        assert "Processed 3 items" in result.stdout
        
        # Verify audit log
        assert audit_log_path.exists()
        
        # Read and parse audit events
        events = []
        with open(audit_log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Should have events for: activate, read (3x), run
        assert len(events) >= 5
        
        # Check event kinds
        event_kinds = [e['kind'] for e in events]
        assert 'activate' in event_kinds  # Instructions loaded
        assert event_kinds.count('read') >= 3  # 2 references + 1 asset
        assert 'run' in event_kinds  # Script execution
        
        # Verify activate event
        activate_events = [e for e in events if e['kind'] == 'activate']
        assert len(activate_events) == 1
        assert activate_events[0]['skill'] == 'complete-skill'
        assert activate_events[0]['path'] == 'SKILL.md'
        assert activate_events[0]['bytes'] > 0
        assert activate_events[0]['sha256'] is not None
        
        # Verify read events
        read_events = [e for e in events if e['kind'] == 'read']
        assert len(read_events) == 3
        
        # Check that all reads are logged
        read_paths = [e['path'] for e in read_events]
        assert 'references/guide.md' in read_paths
        assert 'references/api.json' in read_paths
        assert 'assets/config.bin' in read_paths
        
        # Verify run event
        run_events = [e for e in events if e['kind'] == 'run']
        assert len(run_events) == 1
        assert run_events[0]['skill'] == 'complete-skill'
        assert run_events[0]['path'] == 'scripts/process.py'
        assert run_events[0]['detail']['exit_code'] == 0
        assert run_events[0]['detail']['duration_ms'] > 0
    
    def test_lazy_loading_behavior(self, complete_skill):
        """Test that instructions are truly lazy loaded."""
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        # Create handle without audit sink for simplicity
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=ResourcePolicy(),
            execution_policy=ExecutionPolicy(),
        )
        
        # Instructions should not be loaded yet
        assert handle._instructions_cache is None
        assert handle._body_offset is None
        
        # Load instructions
        instructions = handle.instructions()
        
        # Now they should be cached
        assert handle._instructions_cache is not None
        assert handle._body_offset is not None
        assert instructions == handle._instructions_cache
        
        # Second call should return cached value
        instructions2 = handle.instructions()
        assert instructions2 is instructions  # Same object reference
    
    def test_error_handling_with_audit(self, complete_skill, audit_log_path):
        """Test that errors are properly logged to audit."""
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        # Create restrictive execution policy
        execution_policy = ExecutionPolicy(
            enabled=False,  # Execution disabled
        )
        
        audit_sink = JSONLAuditSink(audit_log_path)
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=ResourcePolicy(),
            execution_policy=execution_policy,
            audit_sink=audit_sink,
        )
        
        # Try to run a script (should fail)
        from agent_skills.exceptions import ScriptExecutionDisabledError
        with pytest.raises(ScriptExecutionDisabledError):
            handle.run_script("process.py")
        
        # Check audit log for error event
        assert audit_log_path.exists()
        
        events = []
        with open(audit_log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Should have an error event
        error_events = [e for e in events if e['kind'] == 'error']
        assert len(error_events) == 1
        assert error_events[0]['skill'] == 'complete-skill'
        assert error_events[0]['path'] == 'scripts/process.py'
        assert 'ScriptExecutionDisabledError' in error_events[0]['detail']['error_type']
    
    def test_session_tracking_across_operations(self, complete_skill):
        """Test that session bytes are tracked across all read operations."""
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        resource_policy = ResourcePolicy(
            allow_binary_assets=True,
        )
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=resource_policy,
            execution_policy=ExecutionPolicy(),
        )
        
        # Initial state
        assert handle._resource_reader.get_session_bytes_read() == 0
        
        # Read a reference
        handle.read_reference("guide.md")
        bytes_after_first = handle._resource_reader.get_session_bytes_read()
        assert bytes_after_first > 0
        
        # Read another reference
        handle.read_reference("api.json")
        bytes_after_second = handle._resource_reader.get_session_bytes_read()
        assert bytes_after_second > bytes_after_first
        
        # Read an asset
        handle.read_asset("config.bin")
        bytes_after_third = handle._resource_reader.get_session_bytes_read()
        assert bytes_after_third > bytes_after_second
        
        # All reads should accumulate
        assert bytes_after_third == (
            bytes_after_first +
            (bytes_after_second - bytes_after_first) +
            (bytes_after_third - bytes_after_second)
        )
    
    def test_multiple_script_executions(self, complete_skill, audit_log_path):
        """Test running multiple scripts in sequence."""
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"complete-skill"},
            allow_scripts_glob=["scripts/*.py"],
        )
        
        audit_sink = JSONLAuditSink(audit_log_path)
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=ResourcePolicy(),
            execution_policy=execution_policy,
            audit_sink=audit_sink,
        )
        
        # Run the same script multiple times with different inputs
        inputs = [
            '["a", "b"]',
            '["x", "y", "z"]',
            '["1"]',
        ]
        
        for input_data in inputs:
            result = handle.run_script("process.py", stdin=input_data)
            assert result.exit_code == 0
            assert "Processed" in result.stdout
        
        # Check audit log
        events = []
        with open(audit_log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Should have 3 run events
        run_events = [e for e in events if e['kind'] == 'run']
        assert len(run_events) == 3
        
        # All should be successful
        for event in run_events:
            assert event['detail']['exit_code'] == 0


class TestSkillHandleRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def test_agent_workflow_simulation(self, complete_skill, audit_log_path):
        """Simulate a typical agent workflow with a skill."""
        # Setup
        descriptor = SkillDescriptor(
            name="complete-skill",
            description="A complete test skill",
            path=complete_skill,
        )
        
        resource_policy = ResourcePolicy(allow_binary_assets=True)
        execution_policy = ExecutionPolicy(
            enabled=True,
            allow_skills={"complete-skill"},
            allow_scripts_glob=["scripts/*.py"],
        )
        audit_sink = JSONLAuditSink(audit_log_path)
        
        handle = SkillHandle(
            descriptor=descriptor,
            resource_policy=resource_policy,
            execution_policy=execution_policy,
            audit_sink=audit_sink,
        )
        
        # Agent workflow:
        # 1. Agent selects skill and reads instructions
        instructions = handle.instructions()
        assert "Complete Skill" in instructions
        
        # 2. Agent reads documentation to understand API
        guide = handle.read_reference("guide.md")
        api_spec = handle.read_reference("api.json")
        assert "User Guide" in guide
        assert "endpoints" in api_spec
        
        # 3. Agent reads configuration asset
        config = handle.read_asset("config.bin")
        assert len(config) == 4
        
        # 4. Agent prepares data and runs processing script
        data = '["task1", "task2", "task3", "task4"]'
        result = handle.run_script("process.py", stdin=data)
        
        # 5. Agent verifies result
        assert result.exit_code == 0
        assert "Processed 4 items" in result.stdout
        
        # Verify complete audit trail
        events = []
        with open(audit_log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Should have complete audit trail
        assert len(events) >= 5
        
        # Verify sequence of operations
        event_kinds = [e['kind'] for e in events]
        assert event_kinds[0] == 'activate'  # Instructions first
        assert 'read' in event_kinds  # Then reads
        assert event_kinds[-1] == 'run'  # Script execution last
