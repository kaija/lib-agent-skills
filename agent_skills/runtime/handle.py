"""Lazy-loading interface for individual skills.

This module provides the SkillHandle class, which serves as the primary interface
for interacting with a skill. It implements lazy loading for instructions, provides
secure access to references and assets, and orchestrates script execution with
comprehensive audit logging.
"""

import hashlib
from datetime import datetime
from pathlib import Path

from agent_skills.exceptions import PolicyViolationError
from agent_skills.exec.runner import ScriptRunner
from agent_skills.models import (
    AuditEvent,
    ExecutionPolicy,
    ExecutionResult,
    ResourcePolicy,
    SkillDescriptor,
)
from agent_skills.observability.audit import AuditSink
from agent_skills.parsing.frontmatter import FrontmatterParser
from agent_skills.parsing.markdown import SkillMarkdownLoader
from agent_skills.resources.reader import ResourceReader
from agent_skills.resources.resolver import PathResolver


class SkillHandle:
    """Lazy-loading interface for individual skill.
    
    SkillHandle provides a secure, policy-enforced interface for accessing skill
    content and executing skill operations. It implements lazy loading for instructions
    (loaded only on first access and cached), and provides methods for reading
    references, assets, and executing scripts.
    
    All operations are subject to security policies (ResourcePolicy and ExecutionPolicy)
    and emit audit events for comprehensive logging.
    
    Example:
        >>> from pathlib import Path
        >>> from agent_skills.models import SkillDescriptor, ResourcePolicy, ExecutionPolicy
        >>> 
        >>> descriptor = SkillDescriptor(
        ...     name="data-processor",
        ...     description="Process CSV data",
        ...     path=Path("/skills/data-processor"),
        ... )
        >>> handle = SkillHandle(
        ...     descriptor=descriptor,
        ...     resource_policy=ResourcePolicy(),
        ...     execution_policy=ExecutionPolicy(enabled=True),
        ... )
        >>> 
        >>> # Lazy load instructions (cached after first call)
        >>> instructions = handle.instructions()
        >>> 
        >>> # Read a reference file
        >>> api_docs = handle.read_reference("api-docs.md")
        >>> 
        >>> # Execute a script
        >>> result = handle.run_script("scripts/process.py", args=["--input", "data.csv"])
    """
    
    def __init__(
        self,
        descriptor: SkillDescriptor,
        resource_policy: ResourcePolicy,
        execution_policy: ExecutionPolicy,
        audit_sink: AuditSink | None = None,
    ):
        """Initialize SkillHandle with descriptor and policies.
        
        Args:
            descriptor: SkillDescriptor containing skill metadata
            resource_policy: ResourcePolicy defining file access limits
            execution_policy: ExecutionPolicy defining script execution permissions
            audit_sink: Optional AuditSink for logging operations
        """
        self._descriptor = descriptor
        self._resource_policy = resource_policy
        self._execution_policy = execution_policy
        self._audit_sink = audit_sink
        
        # Lazy loading state
        self._instructions_cache: str | None = None
        self._body_offset: int | None = None
        
        # Initialize components
        self._path_resolver = PathResolver(descriptor.path)
        self._resource_reader = ResourceReader(resource_policy)
        
        # Script runner will be created lazily when needed
        self._script_runner: ScriptRunner | None = None
    
    def descriptor(self) -> SkillDescriptor:
        """Get skill metadata.
        
        Returns:
            The SkillDescriptor containing skill metadata (name, description, path, etc.)
        """
        return self._descriptor
    
    def instructions(self) -> str:
        """Load and return SKILL.md body (cached after first call).
        
        This method implements lazy loading: on the first call, it parses the
        frontmatter to get the body offset, then loads the markdown body. Subsequent
        calls return the cached content without re-reading the file.
        
        Returns:
            The markdown body content from SKILL.md, with formatting preserved.
            Returns empty string if the body is empty or contains only whitespace.
        
        Raises:
            SkillParseError: If SKILL.md cannot be read or parsed
            
        Note:
            This method emits an audit event with kind="activate" on first load.
        """
        # Return cached instructions if already loaded
        if self._instructions_cache is not None:
            return self._instructions_cache
        
        # Parse frontmatter to get body offset (if not already done)
        if self._body_offset is None:
            parser = FrontmatterParser()
            _, self._body_offset = parser.parse(self._descriptor.path)
        
        # Load the markdown body
        loader = SkillMarkdownLoader()
        body = loader.load_body(self._descriptor.path, self._body_offset)
        
        # Cache the instructions
        self._instructions_cache = body
        
        # Compute SHA256 of the body content
        body_bytes = body.encode('utf-8')
        body_sha256 = hashlib.sha256(body_bytes).hexdigest()
        
        # Emit audit event
        if self._audit_sink:
            event = AuditEvent(
                ts=datetime.now(),
                kind="activate",
                skill=self._descriptor.name,
                path="SKILL.md",
                bytes=len(body_bytes),
                sha256=body_sha256,
                detail={"operation": "load_instructions"},
            )
            self._audit_sink.log(event)
        
        return self._instructions_cache
    
    def read_reference(
        self,
        relpath: str,
        *,
        max_bytes: int | None = None
    ) -> str:
        """Read text file from references/ directory.
        
        This method reads a text file from the skill's references/ directory,
        enforcing path security and size limits from the ResourcePolicy.
        
        Args:
            relpath: Relative path to the file within references/ directory
                    (e.g., "api-docs.md" or "examples/basic.json")
            max_bytes: Optional override for maximum file size
                      (defaults to resource_policy.max_file_bytes)
        
        Returns:
            The file content as a string. Content may be truncated if it exceeds
            size limits (check the truncated flag via audit events).
        
        Raises:
            PathTraversalError: If path contains .. or is absolute
            PolicyViolationError: If path is not within references/ directory
            ResourceTooLargeError: If session byte limit is exceeded
            FileNotFoundError: If the file does not exist
            
        Note:
            This method emits an audit event with kind="read" for each read operation.
            
        Example:
            >>> api_docs = handle.read_reference("api-docs.md")
            >>> example = handle.read_reference("examples/basic.json", max_bytes=10000)
        """
        # Construct full relative path with references/ prefix
        full_relpath = f"references/{relpath}"
        
        # Resolve and validate path
        resolved_path = self._path_resolver.resolve(full_relpath, allowed_dirs=["references"])
        
        # Check if file exists
        if not resolved_path.exists():
            raise FileNotFoundError(f"Reference file not found: {relpath}")
        
        # Check if it's a file (not a directory)
        if not resolved_path.is_file():
            raise PolicyViolationError(f"Reference path is not a file: {relpath}")
        
        # Read the file with size limits
        content, truncated = self._resource_reader.read_text(resolved_path, max_bytes)
        
        # Compute SHA256 of content
        content_sha256 = self._resource_reader.compute_sha256(content)
        
        # Emit audit event
        if self._audit_sink:
            event = AuditEvent(
                ts=datetime.now(),
                kind="read",
                skill=self._descriptor.name,
                path=full_relpath,
                bytes=len(content.encode('utf-8')),
                sha256=content_sha256,
                detail={
                    "operation": "read_reference",
                    "truncated": truncated,
                },
            )
            self._audit_sink.log(event)
        
        return content
    
    def read_asset(
        self,
        relpath: str,
        *,
        max_bytes: int | None = None
    ) -> bytes:
        """Read binary file from assets/ directory.
        
        This method reads a binary file from the skill's assets/ directory,
        enforcing path security and size limits from the ResourcePolicy.
        
        Args:
            relpath: Relative path to the file within assets/ directory
                    (e.g., "diagram.png" or "data/sample.csv")
            max_bytes: Optional override for maximum file size
                      (defaults to resource_policy.binary_max_bytes)
        
        Returns:
            The file content as bytes. Content may be truncated if it exceeds
            size limits (check the truncated flag via audit events).
        
        Raises:
            PathTraversalError: If path contains .. or is absolute
            PolicyViolationError: If path is not within assets/ directory,
                                 or if binary assets are not allowed
            ResourceTooLargeError: If session byte limit is exceeded
            FileNotFoundError: If the file does not exist
            
        Note:
            This method emits an audit event with kind="read" for each read operation.
            Binary assets must be explicitly enabled in ResourcePolicy.
            
        Example:
            >>> image_data = handle.read_asset("diagram.png")
            >>> csv_data = handle.read_asset("data/sample.csv", max_bytes=50000)
        """
        # Check if binary assets are allowed
        if not self._resource_policy.allow_binary_assets:
            raise PolicyViolationError(
                "Binary asset access is disabled in ResourcePolicy. "
                "Set allow_binary_assets=True to enable."
            )
        
        # Construct full relative path with assets/ prefix
        full_relpath = f"assets/{relpath}"
        
        # Resolve and validate path
        resolved_path = self._path_resolver.resolve(full_relpath, allowed_dirs=["assets"])
        
        # Check if file exists
        if not resolved_path.exists():
            raise FileNotFoundError(f"Asset file not found: {relpath}")
        
        # Check if it's a file (not a directory)
        if not resolved_path.is_file():
            raise PolicyViolationError(f"Asset path is not a file: {relpath}")
        
        # Read the file with size limits
        content, truncated = self._resource_reader.read_binary(resolved_path, max_bytes)
        
        # Compute SHA256 of content
        content_sha256 = self._resource_reader.compute_sha256(content)
        
        # Emit audit event
        if self._audit_sink:
            event = AuditEvent(
                ts=datetime.now(),
                kind="read",
                skill=self._descriptor.name,
                path=full_relpath,
                bytes=len(content),
                sha256=content_sha256,
                detail={
                    "operation": "read_asset",
                    "truncated": truncated,
                },
            )
            self._audit_sink.log(event)
        
        return content
    
    def run_script(
        self,
        relpath: str,
        args: list[str] | None = None,
        stdin: str | bytes | None = None,
        timeout_s: int | None = None,
    ) -> ExecutionResult:
        """Execute script from scripts/ directory.
        
        This method executes a script from the skill's scripts/ directory,
        enforcing comprehensive security policies from ExecutionPolicy.
        
        The script execution is subject to:
        - Execution enabled check
        - Skill allowlist check
        - Script glob pattern matching
        - Path security validation
        - Timeout enforcement
        - Environment variable filtering
        
        Args:
            relpath: Relative path to the script within scripts/ directory
                    (e.g., "process.py" or "setup.sh")
            args: Optional list of command-line arguments for the script
            stdin: Optional standard input (string or bytes)
            timeout_s: Optional timeout in seconds (defaults to policy.timeout_s_default)
        
        Returns:
            ExecutionResult containing:
            - exit_code: Script exit code (0 for success)
            - stdout: Standard output as string
            - stderr: Standard error as string
            - duration_ms: Execution duration in milliseconds
            - meta: Execution metadata (sandbox type, etc.)
        
        Raises:
            ScriptExecutionDisabledError: If execution is disabled in policy
            PolicyViolationError: If skill or script not in allowlist
            PathTraversalError: If script path contains traversal or is absolute
            ScriptTimeoutError: If script execution exceeds timeout
            FileNotFoundError: If the script file does not exist
            
        Note:
            This method emits an audit event with kind="run" for each execution.
            Non-zero exit codes are returned in ExecutionResult, not raised as exceptions.
            
        Example:
            >>> result = handle.run_script(
            ...     "scripts/process.py",
            ...     args=["--input", "data.csv"],
            ...     timeout_s=30,
            ... )
            >>> if result.exit_code == 0:
            ...     print("Success:", result.stdout)
            ... else:
            ...     print("Failed:", result.stderr)
        """
        # Construct full relative path with scripts/ prefix
        full_relpath = f"scripts/{relpath}"
        
        # Create script runner lazily
        if self._script_runner is None:
            # Import sandbox here to avoid circular imports
            from agent_skills.exec.local_sandbox import LocalSubprocessSandbox
            sandbox = LocalSubprocessSandbox()
            self._script_runner = ScriptRunner(self._execution_policy, sandbox)
        
        # Execute script with policy enforcement
        # The ScriptRunner will handle all security checks
        try:
            result = self._script_runner.run(
                skill_root=self._descriptor.path,
                skill_name=self._descriptor.name,
                script_relpath=full_relpath,
                args=args,
                stdin=stdin,
                timeout_s=timeout_s,
            )
        except Exception as e:
            # Emit error audit event
            if self._audit_sink:
                error_event = AuditEvent(
                    ts=datetime.now(),
                    kind="error",
                    skill=self._descriptor.name,
                    path=full_relpath,
                    detail={
                        "operation": "run_script",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "args": args,
                    },
                )
                self._audit_sink.log(error_event)
            raise
        
        # Emit audit event for successful execution
        if self._audit_sink:
            event = AuditEvent(
                ts=datetime.now(),
                kind="run",
                skill=self._descriptor.name,
                path=full_relpath,
                detail={
                    "operation": "run_script",
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "args": args,
                    "stdout_bytes": len(result.stdout.encode('utf-8')),
                    "stderr_bytes": len(result.stderr.encode('utf-8')),
                },
            )
            self._audit_sink.log(event)
        
        return result
