"""Integration tests for LocalSubprocessSandbox.

These tests verify the LocalSubprocessSandbox works correctly in realistic
scenarios that match the requirements.
"""

import pytest
import tempfile
from pathlib import Path

from agent_skills.exec.local_sandbox import LocalSubprocessSandbox
from agent_skills.exceptions import ScriptTimeoutError
from agent_skills.models import ExecutionResult


@pytest.fixture
def sandbox():
    """Create a LocalSubprocessSandbox instance."""
    return LocalSubprocessSandbox()


@pytest.fixture
def skill_dir():
    """Create a temporary skill directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_root = Path(tmpdir) / "test-skill"
        skill_root.mkdir()
        
        # Create scripts directory
        scripts_dir = skill_root / "scripts"
        scripts_dir.mkdir()
        
        yield skill_root


def test_requirement_8_2_execute_using_subprocess_run(sandbox, skill_dir):
    """Requirement 8.2: Execute scripts using subprocess.run.
    
    Validates: Requirements 8.2
    """
    # Create a simple script
    script_path = skill_dir / "scripts" / "test.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "print('Executed via subprocess.run')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Verify execution completed successfully
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert "Executed via subprocess.run" in result.stdout


def test_requirement_8_3_capture_stdout_stderr(sandbox, skill_dir):
    """Requirement 8.3: Capture stdout and stderr.
    
    Validates: Requirements 8.3
    """
    # Create a script that writes to both stdout and stderr
    script_path = skill_dir / "scripts" / "output.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('This is stdout')\n"
        "sys.stderr.write('This is stderr\\n')\n"
        "print('More stdout')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Verify both stdout and stderr are captured
    assert "This is stdout" in result.stdout
    assert "More stdout" in result.stdout
    assert "This is stderr" in result.stderr


def test_requirement_8_4_enforce_timeout(sandbox, skill_dir):
    """Requirement 8.4: Enforce timeout.
    
    Validates: Requirements 8.4
    """
    # Create a script that runs longer than timeout
    script_path = skill_dir / "scripts" / "long_running.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "time.sleep(10)\n"
    )
    script_path.chmod(0o755)
    
    # Execute with short timeout
    with pytest.raises(ScriptTimeoutError) as exc_info:
        sandbox.execute(
            script_path=script_path,
            args=[],
            stdin=None,
            timeout_s=1,  # 1 second timeout
            workdir=skill_dir,
            env={"PATH": "/usr/bin:/bin"},
        )
    
    # Verify timeout error is raised
    assert "exceeded 1s timeout" in str(exc_info.value)


def test_requirement_8_5_measure_duration(sandbox, skill_dir):
    """Requirement 8.5: Measure duration.
    
    Validates: Requirements 8.5
    """
    # Create a script with known execution time
    script_path = skill_dir / "scripts" / "timed.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "time.sleep(0.2)  # Sleep for 200ms\n"
        "print('Done')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=None,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Verify duration is measured and reasonable
    assert result.duration_ms >= 200  # At least 200ms
    assert result.duration_ms < 1000  # But less than 1 second
    
    # Verify ExecutionResult contains all required fields
    assert hasattr(result, 'exit_code')
    assert hasattr(result, 'stdout')
    assert hasattr(result, 'stderr')
    assert hasattr(result, 'duration_ms')
    assert hasattr(result, 'meta')
    
    # Verify meta contains sandbox type
    assert result.meta.get('sandbox') == 'local_subprocess'


def test_realistic_data_processing_script(sandbox, skill_dir):
    """Integration test: Realistic data processing scenario."""
    # Create a data file
    data_file = skill_dir / "data.txt"
    data_file.write_text("line1\nline2\nline3\n")
    
    # Create a script that processes the data
    script_path = skill_dir / "scripts" / "process_data.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "\n"
        "# Read input file from argument\n"
        "filename = sys.argv[1]\n"
        "with open(filename, 'r') as f:\n"
        "    lines = f.readlines()\n"
        "\n"
        "# Process: count lines and characters\n"
        "line_count = len(lines)\n"
        "char_count = sum(len(line) for line in lines)\n"
        "\n"
        "print(f'Lines: {line_count}')\n"
        "print(f'Characters: {char_count}')\n"
        "sys.stderr.write(f'Processed {filename}\\n')\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=["data.txt"],
        stdin=None,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Verify processing completed successfully
    assert result.exit_code == 0
    assert "Lines: 3" in result.stdout
    assert "Characters:" in result.stdout
    assert "Processed data.txt" in result.stderr
    assert result.duration_ms > 0


def test_script_with_complex_arguments(sandbox, skill_dir):
    """Integration test: Script with complex command-line arguments."""
    script_path = skill_dir / "scripts" / "complex_args.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "import json\n"
        "\n"
        "# Parse arguments\n"
        "args = sys.argv[1:]\n"
        "result = {\n"
        "    'arg_count': len(args),\n"
        "    'args': args,\n"
        "}\n"
        "print(json.dumps(result, indent=2))\n"
    )
    script_path.chmod(0o755)
    
    result = sandbox.execute(
        script_path=script_path,
        args=["--input", "file.txt", "--output", "result.json", "--verbose"],
        stdin=None,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert '"arg_count": 5' in result.stdout
    assert "--input" in result.stdout
    assert "file.txt" in result.stdout


def test_script_with_stdin_processing(sandbox, skill_dir):
    """Integration test: Script that processes stdin data."""
    script_path = skill_dir / "scripts" / "stdin_processor.py"
    script_path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "import json\n"
        "\n"
        "# Read JSON from stdin\n"
        "data = json.load(sys.stdin)\n"
        "\n"
        "# Process data\n"
        "result = {\n"
        "    'processed': True,\n"
        "    'input_keys': list(data.keys()),\n"
        "    'count': len(data),\n"
        "}\n"
        "\n"
        "print(json.dumps(result))\n"
    )
    script_path.chmod(0o755)
    
    # Prepare JSON input
    input_data = '{"key1": "value1", "key2": "value2", "key3": "value3"}'
    
    result = sandbox.execute(
        script_path=script_path,
        args=[],
        stdin=input_data,
        timeout_s=5,
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    assert result.exit_code == 0
    assert '"processed": true' in result.stdout
    assert '"count": 3' in result.stdout


def test_execution_result_serialization(sandbox, skill_dir):
    """Integration test: Verify ExecutionResult can be serialized."""
    script_path = skill_dir / "scripts" / "simple.py"
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
        workdir=skill_dir,
        env={"PATH": "/usr/bin:/bin"},
    )
    
    # Serialize to dict
    result_dict = result.to_dict()
    
    # Verify all fields are present and JSON-compatible
    assert isinstance(result_dict, dict)
    assert "exit_code" in result_dict
    assert "stdout" in result_dict
    assert "stderr" in result_dict
    assert "duration_ms" in result_dict
    assert "meta" in result_dict
    
    # Verify types are JSON-compatible
    assert isinstance(result_dict["exit_code"], int)
    assert isinstance(result_dict["stdout"], str)
    assert isinstance(result_dict["stderr"], str)
    assert isinstance(result_dict["duration_ms"], int)
    assert isinstance(result_dict["meta"], dict)
    
    # Deserialize back
    from agent_skills.models import ExecutionResult
    restored = ExecutionResult.from_dict(result_dict)
    
    assert restored.exit_code == result.exit_code
    assert restored.stdout == result.stdout
    assert restored.stderr == result.stderr
    assert restored.duration_ms == result.duration_ms
    assert restored.meta == result.meta
