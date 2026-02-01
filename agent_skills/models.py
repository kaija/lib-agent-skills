"""Data models for Agent Skills Runtime."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SkillState(Enum):
    """State machine for skill interaction lifecycle."""
    DISCOVERED = "discovered"
    SELECTED = "selected"
    INSTRUCTIONS_LOADED = "instructions_loaded"
    RESOURCE_NEEDED = "resource_needed"
    SCRIPT_NEEDED = "script_needed"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SkillDescriptor:
    """Metadata-only representation of a skill."""
    name: str
    description: str
    path: Path
    license: str | None = None
    compatibility: dict | None = None
    metadata: dict | None = None
    allowed_tools: list[str] | None = None
    hash: str = ""  # SHA256 of frontmatter
    mtime: float = 0.0
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "license": self.license,
            "compatibility": self.compatibility,
            "metadata": self.metadata,
            "allowed_tools": self.allowed_tools,
            "hash": self.hash,
            "mtime": self.mtime,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillDescriptor":
        """Deserialize from dict."""
        return cls(
            name=data["name"],
            description=data["description"],
            path=Path(data["path"]),
            license=data.get("license"),
            compatibility=data.get("compatibility"),
            metadata=data.get("metadata"),
            allowed_tools=data.get("allowed_tools"),
            hash=data.get("hash", ""),
            mtime=data.get("mtime", 0.0),
        )


@dataclass
class ExecutionResult:
    """Result of script execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    meta: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "meta": self.meta,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionResult":
        """Deserialize from dict."""
        return cls(
            exit_code=data["exit_code"],
            stdout=data["stdout"],
            stderr=data["stderr"],
            duration_ms=data["duration_ms"],
            meta=data.get("meta", {}),
        )


@dataclass
class AuditEvent:
    """Record of a skill operation."""
    ts: datetime
    kind: str  # "scan", "activate", "read", "run", "error"
    skill: str
    path: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    detail: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "ts": self.ts.isoformat(),
            "kind": self.kind,
            "skill": self.skill,
            "path": self.path,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "detail": self.detail,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        """Deserialize from dict."""
        return cls(
            ts=datetime.fromisoformat(data["ts"]),
            kind=data["kind"],
            skill=data["skill"],
            path=data.get("path"),
            bytes=data.get("bytes"),
            sha256=data.get("sha256"),
            detail=data.get("detail", {}),
        )


@dataclass
class SkillSession:
    """Stateful container for agent-skill interaction."""
    session_id: str
    skill_name: str
    state: SkillState
    artifacts: dict = field(default_factory=dict)
    audit: list[AuditEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def transition(self, new_state: SkillState) -> None:
        """Transition to new state with validation."""
        # Define valid state transitions
        valid_transitions = {
            SkillState.DISCOVERED: {SkillState.SELECTED, SkillState.FAILED},
            SkillState.SELECTED: {SkillState.INSTRUCTIONS_LOADED, SkillState.FAILED},
            SkillState.INSTRUCTIONS_LOADED: {
                SkillState.RESOURCE_NEEDED,
                SkillState.SCRIPT_NEEDED,
                SkillState.VERIFYING,
                SkillState.DONE,
                SkillState.FAILED,
            },
            SkillState.RESOURCE_NEEDED: {
                SkillState.SCRIPT_NEEDED,
                SkillState.VERIFYING,
                SkillState.DONE,
                SkillState.FAILED,
            },
            SkillState.SCRIPT_NEEDED: {
                SkillState.VERIFYING,
                SkillState.DONE,
                SkillState.FAILED,
            },
            SkillState.VERIFYING: {SkillState.DONE, SkillState.FAILED},
            SkillState.DONE: set(),  # Terminal state
            SkillState.FAILED: set(),  # Terminal state
        }
        
        if new_state not in valid_transitions.get(self.state, set()):
            raise ValueError(
                f"Invalid state transition from {self.state.value} to {new_state.value}"
            )
        
        self.state = new_state
        self.updated_at = datetime.now()
    
    def add_artifact(self, key: str, value: Any) -> None:
        """Store execution artifact."""
        self.artifacts[key] = value
        self.updated_at = datetime.now()
    
    def add_audit(self, event: AuditEvent) -> None:
        """Append audit event."""
        self.audit.append(event)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "session_id": self.session_id,
            "skill_name": self.skill_name,
            "state": self.state.value,
            "artifacts": self.artifacts,
            "audit": [event.to_dict() for event in self.audit],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillSession":
        """Deserialize from dict."""
        return cls(
            session_id=data["session_id"],
            skill_name=data["skill_name"],
            state=SkillState(data["state"]),
            artifacts=data.get("artifacts", {}),
            audit=[AuditEvent.from_dict(e) for e in data.get("audit", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class ToolResponse:
    """Unified response format for all tools."""
    ok: bool
    type: str  # "metadata", "instructions", "reference", "asset", "execution_result", "error"
    skill: str
    path: str | None = None
    content: str | bytes | dict | None = None
    bytes: int | None = None
    sha256: str | None = None
    truncated: bool = False
    meta: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        # Handle bytes content by converting to base64 or indicating binary
        content = self.content
        if isinstance(content, bytes):
            import base64
            content = base64.b64encode(content).decode("utf-8")
            
        return {
            "ok": self.ok,
            "type": self.type,
            "skill": self.skill,
            "path": self.path,
            "content": content,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "truncated": self.truncated,
            "meta": self.meta,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ToolResponse":
        """Deserialize from dict."""
        content = data.get("content")
        # If content looks like base64 and type suggests binary, decode it
        if isinstance(content, str) and data.get("type") == "asset":
            try:
                import base64
                content = base64.b64decode(content)
            except Exception:
                pass  # Keep as string if decode fails
                
        return cls(
            ok=data["ok"],
            type=data["type"],
            skill=data["skill"],
            path=data.get("path"),
            content=content,
            bytes=data.get("bytes"),
            sha256=data.get("sha256"),
            truncated=data.get("truncated", False),
            meta=data.get("meta", {}),
        )


@dataclass
class ResourcePolicy:
    """Configuration for resource access limits."""
    max_file_bytes: int = 200_000
    max_total_bytes_per_session: int = 1_000_000
    allow_extensions_text: set[str] = field(
        default_factory=lambda: {".md", ".txt", ".json", ".yaml", ".yml"}
    )
    allow_binary_assets: bool = False
    binary_max_bytes: int = 2_000_000
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "max_file_bytes": self.max_file_bytes,
            "max_total_bytes_per_session": self.max_total_bytes_per_session,
            "allow_extensions_text": list(self.allow_extensions_text),
            "allow_binary_assets": self.allow_binary_assets,
            "binary_max_bytes": self.binary_max_bytes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResourcePolicy":
        """Deserialize from dict."""
        return cls(
            max_file_bytes=data.get("max_file_bytes", 200_000),
            max_total_bytes_per_session=data.get("max_total_bytes_per_session", 1_000_000),
            allow_extensions_text=set(data.get("allow_extensions_text", [".md", ".txt", ".json", ".yaml", ".yml"])),
            allow_binary_assets=data.get("allow_binary_assets", False),
            binary_max_bytes=data.get("binary_max_bytes", 2_000_000),
        )


@dataclass
class ExecutionPolicy:
    """Configuration for script execution permissions."""
    enabled: bool = False
    allow_skills: set[str] = field(default_factory=set)
    allow_scripts_glob: list[str] = field(default_factory=list)
    timeout_s_default: int = 60
    network_access: bool = False
    env_allowlist: set[str] = field(default_factory=set)
    workdir_mode: str = "skill_root"  # "skill_root" or "tempdir"
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "enabled": self.enabled,
            "allow_skills": list(self.allow_skills),
            "allow_scripts_glob": self.allow_scripts_glob,
            "timeout_s_default": self.timeout_s_default,
            "network_access": self.network_access,
            "env_allowlist": list(self.env_allowlist),
            "workdir_mode": self.workdir_mode,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionPolicy":
        """Deserialize from dict."""
        return cls(
            enabled=data.get("enabled", False),
            allow_skills=set(data.get("allow_skills", [])),
            allow_scripts_glob=data.get("allow_scripts_glob", []),
            timeout_s_default=data.get("timeout_s_default", 60),
            network_access=data.get("network_access", False),
            env_allowlist=set(data.get("env_allowlist", [])),
            workdir_mode=data.get("workdir_mode", "skill_root"),
        )
