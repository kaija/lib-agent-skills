"""Audit logging interfaces and implementations for Agent Skills Runtime.

This module provides the AuditSink abstract interface for recording skill operations,
along with concrete implementations for different logging backends.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from agent_skills.models import AuditEvent


class AuditSink(ABC):
    """Abstract interface for audit logging.
    
    AuditSink defines the contract for recording audit events from skill operations.
    Implementations can write to different backends (files, stdout, databases, etc.).
    
    All skill operations (scan, activate, read, run, error) should be logged through
    an AuditSink to provide comprehensive audit trails for security and debugging.
    """
    
    @abstractmethod
    def log(self, event: AuditEvent) -> None:
        """Record an audit event.
        
        Args:
            event: The AuditEvent to record, containing timestamp, operation kind,
                   skill name, and operation-specific details.
        
        Raises:
            Implementation-specific exceptions for logging failures.
        """
        pass


class JSONLAuditSink(AuditSink):
    """Writes audit events to a JSONL (JSON Lines) file.
    
    Each audit event is serialized as a single JSON line and appended to the log file.
    This format is easy to parse and process with standard tools like jq, grep, etc.
    
    The log file is opened in append mode, so multiple processes can write to the same
    file (though line-level atomicity depends on the OS and filesystem).
    
    Example log file content:
        {"ts": "2024-01-01T12:00:00", "kind": "scan", "skill": "data-processor", ...}
        {"ts": "2024-01-01T12:00:01", "kind": "activate", "skill": "data-processor", ...}
        {"ts": "2024-01-01T12:00:02", "kind": "read", "skill": "data-processor", ...}
    """
    
    def __init__(self, log_path: Path):
        """Initialize JSONLAuditSink with log file path.
        
        Args:
            log_path: Path to the JSONL log file. Parent directories will be created
                     if they don't exist. The file will be created if it doesn't exist,
                     or appended to if it does.
        """
        self.log_path = Path(log_path)
        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, event: AuditEvent) -> None:
        """Append audit event as a JSON line to the log file.
        
        Args:
            event: The AuditEvent to record.
        
        Raises:
            IOError: If the log file cannot be written to.
            JSONEncodeError: If the event cannot be serialized to JSON.
        """
        # Serialize event to JSON-compatible dict
        event_dict = event.to_dict()
        
        # Write as single JSON line (no pretty printing)
        json_line = json.dumps(event_dict, separators=(',', ':'))
        
        # Append to log file with newline
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json_line + '\n')


class StdoutAuditSink(AuditSink):
    """Writes audit events to stdout.
    
    Each audit event is serialized as a single JSON line and printed to stdout.
    This is useful for debugging and development, or when integrating with logging
    systems that capture stdout (e.g., Docker, Kubernetes, systemd).
    
    Example output:
        {"ts": "2024-01-01T12:00:00", "kind": "scan", "skill": "data-processor", ...}
        {"ts": "2024-01-01T12:00:01", "kind": "activate", "skill": "data-processor", ...}
        {"ts": "2024-01-01T12:00:02", "kind": "read", "skill": "data-processor", ...}
    """
    
    def log(self, event: AuditEvent) -> None:
        """Print audit event as a JSON line to stdout.
        
        Args:
            event: The AuditEvent to record.
        
        Raises:
            JSONEncodeError: If the event cannot be serialized to JSON.
        """
        # Serialize event to JSON-compatible dict
        event_dict = event.to_dict()
        
        # Write as single JSON line (no pretty printing)
        json_line = json.dumps(event_dict, separators=(',', ':'))
        
        # Print to stdout
        print(json_line)
