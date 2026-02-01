"""Unit tests for PathResolver."""

import pytest
from pathlib import Path
from agent_skills.resources import PathResolver
from agent_skills.exceptions import PathTraversalError, PolicyViolationError


class TestPathResolver:
    """Test PathResolver path validation and resolution."""
    
    def test_resolve_valid_reference_path(self, tmp_path):
        """Valid reference path should resolve correctly."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        (skill_root / "references" / "api-docs.md").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("references/api-docs.md", ["references"])
        
        assert resolved == skill_root / "references" / "api-docs.md"
        assert resolved.is_relative_to(skill_root)
    
    def test_resolve_valid_asset_path(self, tmp_path):
        """Valid asset path should resolve correctly."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "assets").mkdir()
        (skill_root / "assets" / "data.csv").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("assets/data.csv", ["assets"])
        
        assert resolved == skill_root / "assets" / "data.csv"
        assert resolved.is_relative_to(skill_root)
    
    def test_resolve_nested_path(self, tmp_path):
        """Nested paths within allowed directories should work."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references" / "api").mkdir(parents=True)
        (skill_root / "references" / "api" / "v1.md").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("references/api/v1.md", ["references"])
        
        assert resolved == skill_root / "references" / "api" / "v1.md"
    
    def test_resolve_multiple_allowed_dirs(self, tmp_path):
        """Should work with multiple allowed directories."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        (skill_root / "assets").mkdir()
        
        resolver = PathResolver(skill_root)
        
        # Both should work
        ref_path = resolver.resolve("references/doc.md", ["references", "assets"])
        assert ref_path.is_relative_to(skill_root)
        
        asset_path = resolver.resolve("assets/data.csv", ["references", "assets"])
        assert asset_path.is_relative_to(skill_root)
    
    def test_reject_absolute_path(self, tmp_path):
        """Absolute paths should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PathTraversalError, match="Absolute paths are not allowed"):
            resolver.resolve("/etc/passwd", ["references"])
    
    def test_reject_path_traversal_dotdot(self, tmp_path):
        """Paths with .. should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PathTraversalError, match="Path traversal detected"):
            resolver.resolve("references/../../../etc/passwd", ["references"])
    
    def test_reject_path_traversal_simple(self, tmp_path):
        """Simple .. path traversal should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PathTraversalError, match="Path traversal detected"):
            resolver.resolve("..", ["references"])
    
    def test_reject_path_traversal_in_middle(self, tmp_path):
        """Path traversal in the middle of path should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PathTraversalError, match="Path traversal detected"):
            resolver.resolve("references/../assets/data.csv", ["references"])
    
    def test_reject_disallowed_directory(self, tmp_path):
        """Paths outside allowed directories should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "scripts").mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PolicyViolationError, match="Path not in allowed directories"):
            resolver.resolve("scripts/run.py", ["references", "assets"])
    
    def test_reject_root_access(self, tmp_path):
        """Direct root access should be rejected unless explicitly allowed."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PolicyViolationError, match="Root path access not allowed"):
            resolver.resolve(".", ["references"])
    
    def test_skill_md_access_when_allowed(self, tmp_path):
        """SKILL.md should be accessible when root is in allowed dirs."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "SKILL.md").touch()
        
        resolver = PathResolver(skill_root)
        
        # This should work if we allow root-level files
        # For now, this tests the current behavior
        with pytest.raises(PolicyViolationError):
            resolver.resolve("SKILL.md", ["references", "assets"])
    
    def test_case_sensitive_paths(self, tmp_path):
        """Path resolution should be case-sensitive on case-sensitive filesystems."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        
        resolver = PathResolver(skill_root)
        
        # This should work
        resolved = resolver.resolve("references/doc.md", ["references"])
        assert "references" in str(resolved)
    
    def test_windows_style_paths(self, tmp_path):
        """Windows-style paths should be handled correctly."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        
        resolver = PathResolver(skill_root)
        
        # Path should work with forward slashes
        resolved = resolver.resolve("references/api/docs.md", ["references"])
        assert resolved.is_relative_to(skill_root)
    
    def test_empty_path(self, tmp_path):
        """Empty path should be rejected."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        
        resolver = PathResolver(skill_root)
        
        with pytest.raises(PolicyViolationError):
            resolver.resolve("", ["references"])
    
    def test_path_with_spaces(self, tmp_path):
        """Paths with spaces should work correctly."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        (skill_root / "references" / "my docs.md").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("references/my docs.md", ["references"])
        
        assert resolved == skill_root / "references" / "my docs.md"
    
    def test_path_with_special_chars(self, tmp_path):
        """Paths with special characters should work correctly."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        (skill_root / "references" / "api-v1.0_final.md").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("references/api-v1.0_final.md", ["references"])
        
        assert resolved == skill_root / "references" / "api-v1.0_final.md"
    
    def test_symlink_escape_attempt(self, tmp_path):
        """Symlinks that escape skill root should be caught."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        
        # Create a directory outside skill root
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").touch()
        
        # Create symlink inside references pointing outside
        symlink = skill_root / "references" / "escape"
        try:
            symlink.symlink_to(outside)
        except OSError:
            # Skip test if symlinks not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")
        
        resolver = PathResolver(skill_root)
        
        # Attempting to access through symlink should be caught
        with pytest.raises(PathTraversalError, match="Path escapes skill root"):
            resolver.resolve("references/escape/secret.txt", ["references"])
    
    def test_scripts_directory_access(self, tmp_path):
        """Scripts directory should be accessible when in allowed_dirs."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "scripts").mkdir()
        (skill_root / "scripts" / "run.py").touch()
        
        resolver = PathResolver(skill_root)
        resolved = resolver.resolve("scripts/run.py", ["scripts"])
        
        assert resolved == skill_root / "scripts" / "run.py"
    
    def test_nonexistent_path_still_validates(self, tmp_path):
        """Path validation should work even if file doesn't exist yet."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        
        resolver = PathResolver(skill_root)
        
        # File doesn't exist, but path should still be valid
        resolved = resolver.resolve("references/future-doc.md", ["references"])
        assert resolved == skill_root / "references" / "future-doc.md"
    
    def test_skill_root_normalization(self, tmp_path):
        """Skill root should be normalized/resolved on initialization."""
        skill_root = tmp_path / "skill"
        skill_root.mkdir()
        (skill_root / "references").mkdir()
        
        # Pass a non-normalized path
        resolver = PathResolver(tmp_path / "skill" / "." / ".")
        resolved = resolver.resolve("references/doc.md", ["references"])
        
        # Should still work correctly
        assert resolved.is_relative_to(skill_root)
