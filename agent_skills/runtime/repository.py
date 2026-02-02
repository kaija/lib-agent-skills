"""Central registry for skill discovery and access.

This module provides the SkillsRepository class, which serves as the main entry point
for the Agent Skills Runtime. It orchestrates skill discovery, caching, and provides
access to individual skills through SkillHandle instances.

The repository implements a lazy loading pattern where only metadata is loaded during
scanning, with full skill content loaded on-demand through SkillHandle.
"""

from datetime import datetime
from pathlib import Path

from agent_skills.discovery.cache import MetadataCache
from agent_skills.discovery.index import SkillIndexer
from agent_skills.discovery.scanner import SkillScanner
from agent_skills.exceptions import SkillNotFoundError
from agent_skills.models import (
    AuditEvent,
    ExecutionPolicy,
    ResourcePolicy,
    SkillDescriptor,
)
from agent_skills.observability.audit import AuditSink
from agent_skills.prompt.claude_xml import ClaudeXMLRenderer
from agent_skills.prompt.json_renderer import JSONRenderer
from agent_skills.runtime.handle import SkillHandle


class SkillsRepository:
    """Central registry for skill discovery and access.
    
    SkillsRepository is the main entry point for the Agent Skills Runtime. It manages
    skill discovery across multiple root directories, maintains a metadata cache for
    fast startup, and provides access to individual skills through SkillHandle instances.
    
    The repository follows a lazy loading pattern:
    1. During refresh(), only YAML frontmatter is parsed (not full SKILL.md body)
    2. Metadata is cached to disk for fast subsequent scans
    3. Full skill content is loaded on-demand through SkillHandle
    
    All skill operations are subject to security policies (ResourcePolicy and
    ExecutionPolicy) and emit audit events for comprehensive logging.
    
    Example:
        >>> from pathlib import Path
        >>> from agent_skills import SkillsRepository, ResourcePolicy, ExecutionPolicy
        >>> 
        >>> # Initialize repository with skill directories
        >>> repo = SkillsRepository(
        ...     roots=[Path("./skills"), Path("~/.agent-skills")],
        ...     cache_dir=Path("~/.cache/agent-skills"),
        ...     resource_policy=ResourcePolicy(),
        ...     execution_policy=ExecutionPolicy(enabled=True),
        ... )
        >>> 
        >>> # Discover all skills
        >>> skills = repo.refresh()
        >>> print(f"Found {len(skills)} skills")
        >>> 
        >>> # List available skills
        >>> for skill in repo.list():
        ...     print(f"- {skill.name}: {skill.description}")
        >>> 
        >>> # Open a specific skill
        >>> handle = repo.open("data-processor")
        >>> instructions = handle.instructions()
    """
    
    def __init__(
        self,
        roots: list[Path],
        cache_dir: Path | None = None,
        resource_policy: ResourcePolicy | None = None,
        execution_policy: ExecutionPolicy | None = None,
        audit_sink: AuditSink | None = None,
    ):
        """Initialize repository with configuration.
        
        Args:
            roots: List of root directories to scan for skills
            cache_dir: Optional directory for caching skill metadata.
                      If None, caching is disabled.
            resource_policy: Optional ResourcePolicy for file access limits.
                           If None, uses default policy.
            execution_policy: Optional ExecutionPolicy for script execution.
                            If None, uses default policy (execution disabled).
            audit_sink: Optional AuditSink for logging operations.
                       If None, audit logging is disabled.
        
        Example:
            >>> repo = SkillsRepository(
            ...     roots=[Path("./skills")],
            ...     cache_dir=Path(".cache"),
            ...     resource_policy=ResourcePolicy(max_file_bytes=100_000),
            ...     execution_policy=ExecutionPolicy(enabled=True),
            ... )
        """
        self._roots = [Path(root).expanduser() for root in roots]
        self._cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self._resource_policy = resource_policy or ResourcePolicy()
        self._execution_policy = execution_policy or ExecutionPolicy()
        self._audit_sink = audit_sink
        
        # Initialize components
        self._scanner = SkillScanner()
        self._indexer = SkillIndexer()
        self._cache = MetadataCache(self._cache_dir) if self._cache_dir else None
        
        # Skill registry (populated by refresh())
        self._skills: dict[str, SkillDescriptor] = {}
    
    def refresh(self) -> list[SkillDescriptor]:
        """Scan roots and update skill index.
        
        This method performs the following steps:
        1. Scans all root directories for SKILL.md files
        2. For each discovered skill:
           - Checks if cached metadata is valid (matching mtime and hash)
           - If cache is valid, uses cached metadata
           - If cache is invalid or missing, parses frontmatter and updates cache
        3. Updates the internal skill registry
        4. Emits audit events for the scan operation
        
        Returns:
            List of all discovered SkillDescriptor objects
            
        Note:
            This method only parses YAML frontmatter, not the full SKILL.md body.
            Full content is loaded on-demand through SkillHandle.
            
        Example:
            >>> repo = SkillsRepository(roots=[Path("./skills")])
            >>> skills = repo.refresh()
            >>> print(f"Discovered {len(skills)} skills")
            >>> for skill in skills:
            ...     print(f"- {skill.name}: {skill.description}")
        """
        # Scan for skill directories
        skill_paths = self._scanner.scan(self._roots)
        
        # Process each skill path
        descriptors = []
        for skill_path in skill_paths:
            # Try to get from cache first
            descriptor = None
            if self._cache:
                descriptor = self._cache.get(skill_path)
            
            # If not in cache or cache is invalid, parse and index
            if descriptor is None:
                # Parse and create descriptor
                parsed_descriptors = self._indexer.index_skills([skill_path])
                if parsed_descriptors:
                    descriptor = parsed_descriptors[0]
                    
                    # Update cache
                    if self._cache:
                        self._cache.put(descriptor)
            
            # Add to results if we have a valid descriptor
            if descriptor:
                descriptors.append(descriptor)
                
                # Emit scan audit event
                if self._audit_sink:
                    event = AuditEvent(
                        ts=datetime.now(),
                        kind="scan",
                        skill=descriptor.name,
                        path=str(descriptor.path),
                        detail={
                            "operation": "skill_discovery",
                            "cached": self._cache is not None and self._cache.get(skill_path) is not None,
                        },
                    )
                    self._audit_sink.log(event)
        
        # Update internal registry
        self._skills = {desc.name: desc for desc in descriptors}
        
        return descriptors
    
    def list(self) -> list[SkillDescriptor]:
        """Return all discovered skill descriptors.
        
        Returns:
            List of SkillDescriptor objects for all skills in the registry.
            Returns empty list if refresh() has not been called yet.
            
        Note:
            This method returns cached results from the last refresh() call.
            Call refresh() first to discover skills, or call it again to
            update the list if skills have been added/removed.
            
        Example:
            >>> repo = SkillsRepository(roots=[Path("./skills")])
            >>> repo.refresh()
            >>> skills = repo.list()
            >>> for skill in skills:
            ...     print(f"{skill.name}: {skill.description}")
        """
        return list(self._skills.values())
    
    def open(self, name: str) -> SkillHandle:
        """Get lazy SkillHandle for a skill.
        
        This method returns a SkillHandle instance that provides lazy-loading
        access to the skill's content and operations. The handle enforces
        security policies and emits audit events for all operations.
        
        Args:
            name: Name of the skill to open (from SkillDescriptor.name)
            
        Returns:
            SkillHandle instance for the requested skill
            
        Raises:
            SkillNotFoundError: If the skill name is not in the registry
            
        Note:
            The skill must have been discovered by a previous refresh() call.
            The returned handle uses lazy loading - no content is loaded until
            you call methods like instructions(), read_reference(), etc.
            
        Example:
            >>> repo = SkillsRepository(roots=[Path("./skills")])
            >>> repo.refresh()
            >>> 
            >>> # Open a skill
            >>> handle = repo.open("data-processor")
            >>> 
            >>> # Access skill content (lazy loaded)
            >>> instructions = handle.instructions()
            >>> api_docs = handle.read_reference("api-docs.md")
        """
        # Check if skill exists in registry
        if name not in self._skills:
            raise SkillNotFoundError(
                f"Skill '{name}' not found in repository. "
                f"Available skills: {', '.join(self._skills.keys())}"
            )
        
        # Get descriptor
        descriptor = self._skills[name]
        
        # Create and return SkillHandle
        return SkillHandle(
            descriptor=descriptor,
            resource_policy=self._resource_policy,
            execution_policy=self._execution_policy,
            audit_sink=self._audit_sink,
        )
    
    def to_prompt(
        self,
        format: str = "claude_xml",
        include_location: bool = True
    ) -> str:
        """Render available skills for agent prompt.
        
        This method renders the list of discovered skills in a format suitable
        for injection into agent prompts. The output format can be customized
        to match different agent frameworks and preferences.
        
        Args:
            format: Output format, either "claude_xml" or "json".
                   - "claude_xml": Renders as <available_skills> XML format
                   - "json": Renders as JSON array
                   Defaults to "claude_xml".
            include_location: Whether to include filesystem path in output.
                            Defaults to True.
        
        Returns:
            Formatted string representation of available skills
            
        Raises:
            ValueError: If format is not "claude_xml" or "json"
            
        Note:
            This method uses the skills discovered by the last refresh() call.
            Call refresh() first to ensure the skill list is up-to-date.
            
        Example:
            >>> repo = SkillsRepository(roots=[Path("./skills")])
            >>> repo.refresh()
            >>> 
            >>> # Claude XML format
            >>> claude_prompt = repo.to_prompt(format="claude_xml", include_location=True)
            >>> print(claude_prompt)
            <available_skills>
              <skill name="data-processor" description="Process CSV data" location="/path/to/skills/data-processor" />
              <skill name="api-client" description="Call external APIs" location="/path/to/skills/api-client" />
            </available_skills>
            >>> 
            >>> # JSON format
            >>> json_prompt = repo.to_prompt(format="json", include_location=False)
            >>> print(json_prompt)
            [
              {"name": "data-processor", "description": "Process CSV data"},
              {"name": "api-client", "description": "Call external APIs"}
            ]
        """
        # Validate format parameter
        if format not in ("claude_xml", "json"):
            raise ValueError(
                f"Invalid format '{format}'. Must be 'claude_xml' or 'json'."
            )
        
        # Get list of skills
        skills = self.list()
        
        # Delegate to appropriate renderer
        if format == "claude_xml":
            renderer = ClaudeXMLRenderer()
            return renderer.render(skills, include_location=include_location)
        else:  # format == "json"
            renderer = JSONRenderer()
            return renderer.render(skills, include_location=include_location)
    

