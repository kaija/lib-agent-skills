"""Unit tests for AuditSink interface."""

import json
import pytest
from datetime import datetime
from pathlib import Path
from agent_skills.observability.audit import AuditSink, JSONLAuditSink, StdoutAuditSink
from agent_skills.models import AuditEvent


class ConcreteAuditSink(AuditSink):
    """Concrete implementation of AuditSink for testing."""
    
    def __init__(self):
        self.events = []
    
    def log(self, event: AuditEvent) -> None:
        """Record event in memory."""
        self.events.append(event)


class TestAuditSink:
    """Tests for AuditSink abstract interface."""
    
    def test_abstract_interface(self):
        """Test that AuditSink cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AuditSink()
    
    def test_concrete_implementation(self):
        """Test that concrete implementations can be instantiated."""
        sink = ConcreteAuditSink()
        assert sink is not None
        assert isinstance(sink, AuditSink)
    
    def test_log_method_required(self):
        """Test that log method must be implemented."""
        # Attempt to create a class without implementing log
        with pytest.raises(TypeError):
            class IncompleteAuditSink(AuditSink):
                pass
            IncompleteAuditSink()
    
    def test_log_scan_event(self):
        """Test logging a scan event."""
        sink = ConcreteAuditSink()
        event = AuditEvent(
            ts=datetime.now(),
            kind="scan",
            skill="test-skill",
            path="/path/to/skill",
            detail={"skills_found": 5}
        )
        
        sink.log(event)
        
        assert len(sink.events) == 1
        assert sink.events[0].kind == "scan"
        assert sink.events[0].skill == "test-skill"
    
    def test_log_activate_event(self):
        """Test logging an activate event."""
        sink = ConcreteAuditSink()
        event = AuditEvent(
            ts=datetime.now(),
            kind="activate",
            skill="data-processor",
            path="SKILL.md",
            bytes=1234,
            sha256="abc123",
            detail={"instructions_loaded": True}
        )
        
        sink.log(event)
        
        assert len(sink.events) == 1
        assert sink.events[0].kind == "activate"
        assert sink.events[0].bytes == 1234
        assert sink.events[0].sha256 == "abc123"
    
    def test_log_read_event(self):
        """Test logging a read event."""
        sink = ConcreteAuditSink()
        event = AuditEvent(
            ts=datetime.now(),
            kind="read",
            skill="api-client",
            path="references/api-docs.md",
            bytes=5678,
            sha256="def456",
            detail={"truncated": False}
        )
        
        sink.log(event)
        
        assert len(sink.events) == 1
        assert sink.events[0].kind == "read"
        assert sink.events[0].path == "references/api-docs.md"
    
    def test_log_run_event(self):
        """Test logging a run event."""
        sink = ConcreteAuditSink()
        event = AuditEvent(
            ts=datetime.now(),
            kind="run",
            skill="data-processor",
            path="scripts/process.py",
            detail={
                "args": ["--input", "data.csv"],
                "exit_code": 0,
                "duration_ms": 1234
            }
        )
        
        sink.log(event)
        
        assert len(sink.events) == 1
        assert sink.events[0].kind == "run"
        assert sink.events[0].detail["exit_code"] == 0
    
    def test_log_error_event(self):
        """Test logging an error event."""
        sink = ConcreteAuditSink()
        event = AuditEvent(
            ts=datetime.now(),
            kind="error",
            skill="malicious-skill",
            path="../../etc/passwd",
            detail={
                "error_type": "PathTraversalError",
                "error_message": "Path traversal detected"
            }
        )
        
        sink.log(event)
        
        assert len(sink.events) == 1
        assert sink.events[0].kind == "error"
        assert sink.events[0].detail["error_type"] == "PathTraversalError"
    
    def test_log_multiple_events(self):
        """Test logging multiple events in sequence."""
        sink = ConcreteAuditSink()
        
        events = [
            AuditEvent(ts=datetime.now(), kind="scan", skill="skill1"),
            AuditEvent(ts=datetime.now(), kind="activate", skill="skill1"),
            AuditEvent(ts=datetime.now(), kind="read", skill="skill1", path="ref.md"),
            AuditEvent(ts=datetime.now(), kind="run", skill="skill1", path="script.py"),
        ]
        
        for event in events:
            sink.log(event)
        
        assert len(sink.events) == 4
        assert [e.kind for e in sink.events] == ["scan", "activate", "read", "run"]
    
    def test_event_timestamp_preserved(self):
        """Test that event timestamps are preserved."""
        sink = ConcreteAuditSink()
        ts = datetime(2024, 1, 1, 12, 0, 0)
        event = AuditEvent(
            ts=ts,
            kind="activate",
            skill="test-skill"
        )
        
        sink.log(event)
        
        assert sink.events[0].ts == ts
    
    def test_event_details_preserved(self):
        """Test that event details are preserved."""
        sink = ConcreteAuditSink()
        detail = {
            "key1": "value1",
            "key2": 123,
            "key3": True,
            "nested": {"inner": "data"}
        }
        event = AuditEvent(
            ts=datetime.now(),
            kind="scan",
            skill="test-skill",
            detail=detail
        )
        
        sink.log(event)
        
        assert sink.events[0].detail == detail
        assert sink.events[0].detail["nested"]["inner"] == "data"


class TestJSONLAuditSink:
    """Tests for JSONLAuditSink implementation."""
    
    def test_initialization(self, tmp_path):
        """Test that JSONLAuditSink can be initialized with a path."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        assert sink.log_path == log_path
        assert isinstance(sink, AuditSink)
    
    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        log_path = tmp_path / "nested" / "dir" / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        assert log_path.parent.exists()
        assert log_path.parent.is_dir()
    
    def test_log_single_event(self, tmp_path):
        """Test logging a single event to JSONL file."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            path="/path/to/skill",
            detail={"skills_found": 5}
        )
        
        sink.log(event)
        
        # Verify file was created
        assert log_path.exists()
        
        # Read and parse the JSON line
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        logged_event = json.loads(lines[0])
        
        assert logged_event["ts"] == "2024-01-01T12:00:00"
        assert logged_event["kind"] == "scan"
        assert logged_event["skill"] == "test-skill"
        assert logged_event["path"] == "/path/to/skill"
        assert logged_event["detail"]["skills_found"] == 5
    
    def test_log_multiple_events(self, tmp_path):
        """Test logging multiple events appends to file."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        events = [
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 0), kind="scan", skill="skill1"),
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 1), kind="activate", skill="skill1"),
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 2), kind="read", skill="skill1", path="ref.md"),
        ]
        
        for event in events:
            sink.log(event)
        
        # Read all lines
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Verify each line is valid JSON
        for i, line in enumerate(lines):
            logged_event = json.loads(line)
            assert logged_event["kind"] == events[i].kind
            assert logged_event["skill"] == events[i].skill
    
    def test_log_with_all_fields(self, tmp_path):
        """Test logging an event with all fields populated."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="read",
            skill="data-processor",
            path="references/api-docs.md",
            bytes=5678,
            sha256="abc123def456",
            detail={"truncated": False, "encoding": "utf-8"}
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            logged_event = json.loads(f.read())
        
        assert logged_event["ts"] == "2024-01-01T12:00:00"
        assert logged_event["kind"] == "read"
        assert logged_event["skill"] == "data-processor"
        assert logged_event["path"] == "references/api-docs.md"
        assert logged_event["bytes"] == 5678
        assert logged_event["sha256"] == "abc123def456"
        assert logged_event["detail"]["truncated"] is False
        assert logged_event["detail"]["encoding"] == "utf-8"
    
    def test_log_with_optional_fields_none(self, tmp_path):
        """Test logging an event with optional fields set to None."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            path=None,
            bytes=None,
            sha256=None,
            detail={}
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            logged_event = json.loads(f.read())
        
        assert logged_event["path"] is None
        assert logged_event["bytes"] is None
        assert logged_event["sha256"] is None
        assert logged_event["detail"] == {}
    
    def test_append_mode(self, tmp_path):
        """Test that logging appends to existing file."""
        log_path = tmp_path / "audit.jsonl"
        
        # Write first event
        sink1 = JSONLAuditSink(log_path)
        event1 = AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 0), kind="scan", skill="skill1")
        sink1.log(event1)
        
        # Create new sink instance and write second event
        sink2 = JSONLAuditSink(log_path)
        event2 = AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 1), kind="activate", skill="skill2")
        sink2.log(event2)
        
        # Verify both events are in the file
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert json.loads(lines[0])["skill"] == "skill1"
        assert json.loads(lines[1])["skill"] == "skill2"
    
    def test_jsonl_format_no_pretty_print(self, tmp_path):
        """Test that JSON is compact (no pretty printing)."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            detail={"nested": {"data": "value"}}
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should be a single line (no newlines except at the end)
        lines = content.strip().split('\n')
        assert len(lines) == 1
        
        # Should not contain extra whitespace (compact JSON)
        assert '  ' not in content  # No double spaces
        assert '\n' not in content.strip()  # No internal newlines
    
    def test_unicode_handling(self, tmp_path):
        """Test that unicode characters are handled correctly."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="read",
            skill="unicode-skill",
            path="références/文档.md",
            detail={"message": "Hello 世界 🌍"}
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            logged_event = json.loads(f.read())
        
        assert logged_event["path"] == "références/文档.md"
        assert logged_event["detail"]["message"] == "Hello 世界 🌍"
    
    def test_error_event_logging(self, tmp_path):
        """Test logging error events with error details."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="error",
            skill="malicious-skill",
            path="../../etc/passwd",
            detail={
                "error_type": "PathTraversalError",
                "error_message": "Path traversal detected",
                "attempted_path": "../../etc/passwd"
            }
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            logged_event = json.loads(f.read())
        
        assert logged_event["kind"] == "error"
        assert logged_event["detail"]["error_type"] == "PathTraversalError"
        assert logged_event["detail"]["error_message"] == "Path traversal detected"
    
    def test_execution_event_logging(self, tmp_path):
        """Test logging script execution events."""
        log_path = tmp_path / "audit.jsonl"
        sink = JSONLAuditSink(log_path)
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="run",
            skill="data-processor",
            path="scripts/process.py",
            detail={
                "args": ["--input", "data.csv", "--output", "result.json"],
                "exit_code": 0,
                "duration_ms": 1234,
                "stdout_bytes": 567,
                "stderr_bytes": 0
            }
        )
        
        sink.log(event)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            logged_event = json.loads(f.read())
        
        assert logged_event["kind"] == "run"
        assert logged_event["path"] == "scripts/process.py"
        assert logged_event["detail"]["exit_code"] == 0
        assert logged_event["detail"]["duration_ms"] == 1234
        assert logged_event["detail"]["args"] == ["--input", "data.csv", "--output", "result.json"]


class TestStdoutAuditSink:
    """Tests for StdoutAuditSink implementation."""
    
    def test_initialization(self):
        """Test that StdoutAuditSink can be initialized."""
        sink = StdoutAuditSink()
        
        assert sink is not None
        assert isinstance(sink, AuditSink)
    
    def test_log_single_event(self, capsys):
        """Test logging a single event to stdout."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            path="/path/to/skill",
            detail={"skills_found": 5}
        )
        
        sink.log(event)
        
        # Capture stdout
        captured = capsys.readouterr()
        
        # Parse the JSON output
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["ts"] == "2024-01-01T12:00:00"
        assert logged_event["kind"] == "scan"
        assert logged_event["skill"] == "test-skill"
        assert logged_event["path"] == "/path/to/skill"
        assert logged_event["detail"]["skills_found"] == 5
    
    def test_log_multiple_events(self, capsys):
        """Test logging multiple events to stdout."""
        sink = StdoutAuditSink()
        
        events = [
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 0), kind="scan", skill="skill1"),
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 1), kind="activate", skill="skill1"),
            AuditEvent(ts=datetime(2024, 1, 1, 12, 0, 2), kind="read", skill="skill1", path="ref.md"),
        ]
        
        for event in events:
            sink.log(event)
        
        # Capture stdout
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        
        assert len(lines) == 3
        
        # Verify each line is valid JSON
        for i, line in enumerate(lines):
            logged_event = json.loads(line)
            assert logged_event["kind"] == events[i].kind
            assert logged_event["skill"] == events[i].skill
    
    def test_log_with_all_fields(self, capsys):
        """Test logging an event with all fields populated."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="read",
            skill="data-processor",
            path="references/api-docs.md",
            bytes=5678,
            sha256="abc123def456",
            detail={"truncated": False, "encoding": "utf-8"}
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["ts"] == "2024-01-01T12:00:00"
        assert logged_event["kind"] == "read"
        assert logged_event["skill"] == "data-processor"
        assert logged_event["path"] == "references/api-docs.md"
        assert logged_event["bytes"] == 5678
        assert logged_event["sha256"] == "abc123def456"
        assert logged_event["detail"]["truncated"] is False
        assert logged_event["detail"]["encoding"] == "utf-8"
    
    def test_log_with_optional_fields_none(self, capsys):
        """Test logging an event with optional fields set to None."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            path=None,
            bytes=None,
            sha256=None,
            detail={}
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["path"] is None
        assert logged_event["bytes"] is None
        assert logged_event["sha256"] is None
        assert logged_event["detail"] == {}
    
    def test_json_format_no_pretty_print(self, capsys):
        """Test that JSON is compact (no pretty printing)."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="scan",
            skill="test-skill",
            detail={"nested": {"data": "value"}}
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        content = captured.out.strip()
        
        # Should be a single line
        lines = content.split('\n')
        assert len(lines) == 1
        
        # Should not contain extra whitespace (compact JSON)
        # The separators=(',', ':') ensures no spaces after commas or colons
        assert ': ' not in content  # No space after colon
        assert ', ' not in content  # No space after comma
    
    def test_unicode_handling(self, capsys):
        """Test that unicode characters are handled correctly."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="read",
            skill="unicode-skill",
            path="références/文档.md",
            detail={"message": "Hello 世界 🌍"}
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["path"] == "références/文档.md"
        assert logged_event["detail"]["message"] == "Hello 世界 🌍"
    
    def test_error_event_logging(self, capsys):
        """Test logging error events with error details."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="error",
            skill="malicious-skill",
            path="../../etc/passwd",
            detail={
                "error_type": "PathTraversalError",
                "error_message": "Path traversal detected",
                "attempted_path": "../../etc/passwd"
            }
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["kind"] == "error"
        assert logged_event["detail"]["error_type"] == "PathTraversalError"
        assert logged_event["detail"]["error_message"] == "Path traversal detected"
    
    def test_execution_event_logging(self, capsys):
        """Test logging script execution events."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="run",
            skill="data-processor",
            path="scripts/process.py",
            detail={
                "args": ["--input", "data.csv", "--output", "result.json"],
                "exit_code": 0,
                "duration_ms": 1234,
                "stdout_bytes": 567,
                "stderr_bytes": 0
            }
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["kind"] == "run"
        assert logged_event["path"] == "scripts/process.py"
        assert logged_event["detail"]["exit_code"] == 0
        assert logged_event["detail"]["duration_ms"] == 1234
        assert logged_event["detail"]["args"] == ["--input", "data.csv", "--output", "result.json"]
    
    def test_activate_event_logging(self, capsys):
        """Test logging activate events."""
        sink = StdoutAuditSink()
        
        event = AuditEvent(
            ts=datetime(2024, 1, 1, 12, 0, 0),
            kind="activate",
            skill="data-processor",
            path="SKILL.md",
            bytes=1234,
            sha256="abc123",
            detail={"instructions_loaded": True}
        )
        
        sink.log(event)
        
        captured = capsys.readouterr()
        logged_event = json.loads(captured.out.strip())
        
        assert logged_event["kind"] == "activate"
        assert logged_event["bytes"] == 1234
        assert logged_event["sha256"] == "abc123"
        assert logged_event["detail"]["instructions_loaded"] is True
