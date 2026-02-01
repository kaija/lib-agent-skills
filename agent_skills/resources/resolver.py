"""Path resolution and validation for skill resources."""

from pathlib import Path
from agent_skills.exceptions import PathTraversalError, PolicyViolationError


class PathResolver:
    """Validates and resolves paths within skill directory."""
    
    def __init__(self, skill_root: Path):
        """Initialize with skill root directory.
        
        Args:
            skill_root: The root directory of the skill
        """
        self.skill_root = skill_root.resolve()
    
    def resolve(self, relpath: str, allowed_dirs: list[str]) -> Path:
        """Resolve relative path and validate security constraints.
        
        This method ensures that:
        1. The path does not contain path traversal attempts (..)
        2. The path is not absolute
        3. The resolved path is within the skill root directory
        4. The path is within one of the allowed directories
        
        Args:
            relpath: Relative path to resolve (e.g., "references/api-docs.md")
            allowed_dirs: List of allowed directory names (e.g., ["references", "assets"])
        
        Returns:
            Resolved absolute Path object
            
        Raises:
            PathTraversalError: If path contains .. or is absolute
            PolicyViolationError: If path is not within allowed directories
        """
        # Check for absolute paths
        if Path(relpath).is_absolute():
            raise PathTraversalError(
                f"Absolute paths are not allowed: {relpath}"
            )
        
        # Check for path traversal attempts (..)
        if ".." in Path(relpath).parts:
            raise PathTraversalError(
                f"Path traversal detected (.. component): {relpath}"
            )
        
        # Resolve the path relative to skill root
        resolved_path = (self.skill_root / relpath).resolve()
        
        # Verify the resolved path is within skill root
        # This is a defense-in-depth check even after the .. check
        try:
            resolved_path.relative_to(self.skill_root)
        except ValueError:
            raise PathTraversalError(
                f"Path escapes skill root: {relpath} -> {resolved_path}"
            )
        
        # Check if path is within allowed directories
        # Get the relative path from skill root
        rel_from_root = resolved_path.relative_to(self.skill_root)
        
        # Check if the first component matches any allowed directory
        if rel_from_root.parts:
            first_component = rel_from_root.parts[0]
            if first_component not in allowed_dirs:
                raise PolicyViolationError(
                    f"Path not in allowed directories {allowed_dirs}: {relpath}"
                )
        else:
            # Empty path or root - not allowed unless explicitly in allowed_dirs
            if "" not in allowed_dirs and "." not in allowed_dirs:
                raise PolicyViolationError(
                    f"Root path access not allowed: {relpath}"
                )
        
        return resolved_path
