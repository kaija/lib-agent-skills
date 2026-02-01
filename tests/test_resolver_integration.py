"""Integration tests for PathResolver."""

import pytest
from pathlib import Path
from agent_skills.resources import PathResolver
from agent_skills.exceptions import PathTraversalError, PolicyViolationError


class TestPathResolverIntegration:
    """Integration tests for PathResolver with realistic skill structures."""
    
    @pytest.fixture
    def skill_structure(self, tmp_path):
        """Create a realistic skill directory structure."""
        skill_root = tmp_path / "data-processor"
        skill_root.mkdir()
        
        # Create SKILL.md
        (skill_root / "SKILL.md").write_text("""---
name: data-processor
description: Process CSV data
---

# Instructions
Process data files.
""")
        
        # Create references directory with nested structure
        refs = skill_root / "references"
        refs.mkdir()
        (refs / "README.md").write_text("# References")
        (refs / "api").mkdir()
        (refs / "api" / "v1.md").write_text("# API v1")
        (refs / "api" / "v2.md").write_text("# API v2")
        (refs / "examples").mkdir()
        (refs / "examples" / "basic.json").write_text('{"example": "data"}')
        
        # Create assets directory
        assets = skill_root / "assets"
        assets.mkdir()
        (assets / "sample.csv").write_text("col1,col2\n1,2\n")
        (assets / "data").mkdir()
        (assets / "data" / "large.csv").write_text("a,b,c\n" * 100)
        
        # Create scripts directory
        scripts = skill_root / "scripts"
        scripts.mkdir()
        (scripts / "process.py").write_text("#!/usr/bin/env python\nprint('processing')")
        (scripts / "utils").mkdir()
        (scripts / "utils" / "helper.py").write_text("def help(): pass")
        
        return skill_root
    
    def test_access_all_reference_files(self, skill_structure):
        """Should be able to access all files in references directory."""
        resolver = PathResolver(skill_structure)
        
        # Access root-level reference
        readme = resolver.resolve("references/README.md", ["references"])
        assert readme.exists()
        assert readme.read_text() == "# References"
        
        # Access nested references
        api_v1 = resolver.resolve("references/api/v1.md", ["references"])
        assert api_v1.exists()
        
        api_v2 = resolver.resolve("references/api/v2.md", ["references"])
        assert api_v2.exists()
        
        # Access examples
        example = resolver.resolve("references/examples/basic.json", ["references"])
        assert example.exists()
    
    def test_access_all_asset_files(self, skill_structure):
        """Should be able to access all files in assets directory."""
        resolver = PathResolver(skill_structure)
        
        # Access root-level asset
        sample = resolver.resolve("assets/sample.csv", ["assets"])
        assert sample.exists()
        
        # Access nested asset
        large = resolver.resolve("assets/data/large.csv", ["assets"])
        assert large.exists()
    
    def test_access_all_script_files(self, skill_structure):
        """Should be able to access all files in scripts directory."""
        resolver = PathResolver(skill_structure)
        
        # Access root-level script
        process = resolver.resolve("scripts/process.py", ["scripts"])
        assert process.exists()
        
        # Access nested script
        helper = resolver.resolve("scripts/utils/helper.py", ["scripts"])
        assert helper.exists()
    
    def test_cannot_cross_directory_boundaries(self, skill_structure):
        """Should not be able to access files outside allowed directories."""
        resolver = PathResolver(skill_structure)
        
        # Cannot access scripts from references allowlist
        with pytest.raises(PolicyViolationError):
            resolver.resolve("scripts/process.py", ["references"])
        
        # Cannot access references from assets allowlist
        with pytest.raises(PolicyViolationError):
            resolver.resolve("references/README.md", ["assets"])
        
        # Cannot access assets from scripts allowlist
        with pytest.raises(PolicyViolationError):
            resolver.resolve("assets/sample.csv", ["scripts"])
    
    def test_cannot_escape_via_traversal(self, skill_structure):
        """Should not be able to escape skill root via path traversal."""
        resolver = PathResolver(skill_structure)
        
        # Try to escape from references
        with pytest.raises(PathTraversalError):
            resolver.resolve("references/../../etc/passwd", ["references"])
        
        # Try to escape from nested directory
        with pytest.raises(PathTraversalError):
            resolver.resolve("references/api/../../../etc/passwd", ["references"])
    
    def test_multiple_allowed_directories(self, skill_structure):
        """Should work correctly with multiple allowed directories."""
        resolver = PathResolver(skill_structure)
        
        # Allow both references and assets
        allowed = ["references", "assets"]
        
        # Should access references
        ref = resolver.resolve("references/README.md", allowed)
        assert ref.exists()
        
        # Should access assets
        asset = resolver.resolve("assets/sample.csv", allowed)
        assert asset.exists()
        
        # Should not access scripts
        with pytest.raises(PolicyViolationError):
            resolver.resolve("scripts/process.py", allowed)
    
    def test_realistic_read_workflow(self, skill_structure):
        """Test a realistic workflow of reading multiple files."""
        resolver = PathResolver(skill_structure)
        
        # Agent wants to read documentation
        files_to_read = [
            "references/README.md",
            "references/api/v1.md",
            "references/examples/basic.json",
        ]
        
        for file_path in files_to_read:
            resolved = resolver.resolve(file_path, ["references"])
            assert resolved.exists()
            content = resolved.read_text()
            assert len(content) > 0
    
    def test_realistic_script_execution_workflow(self, skill_structure):
        """Test a realistic workflow of validating script paths."""
        resolver = PathResolver(skill_structure)
        
        # Agent wants to execute scripts
        scripts_to_run = [
            "scripts/process.py",
            "scripts/utils/helper.py",
        ]
        
        for script_path in scripts_to_run:
            resolved = resolver.resolve(script_path, ["scripts"])
            assert resolved.exists()
            assert resolved.suffix == ".py"
    
    def test_malicious_path_attempts(self, skill_structure):
        """Test various malicious path attempts are blocked."""
        resolver = PathResolver(skill_structure)
        
        malicious_paths = [
            "../../../etc/passwd",
            "references/../../../etc/passwd",
            "references/api/../../../../../../etc/passwd",
            "/etc/passwd",
            "/tmp/malicious",
            "references/../scripts/process.py",  # Try to access scripts via traversal
        ]
        
        for malicious in malicious_paths:
            with pytest.raises((PathTraversalError, PolicyViolationError)):
                resolver.resolve(malicious, ["references"])
    
    def test_edge_case_paths(self, skill_structure):
        """Test edge case paths are handled correctly."""
        resolver = PathResolver(skill_structure)
        
        # Empty path
        with pytest.raises(PolicyViolationError):
            resolver.resolve("", ["references"])
        
        # Just a dot
        with pytest.raises(PolicyViolationError):
            resolver.resolve(".", ["references"])
        
        # Just allowed directory name (no file)
        # This should work - it's the directory itself
        resolved = resolver.resolve("references", ["references"])
        assert resolved == skill_structure / "references"
    
    def test_path_normalization(self, skill_structure):
        """Test that paths are properly normalized."""
        resolver = PathResolver(skill_structure)
        
        # Path with redundant separators
        resolved = resolver.resolve("references//api///v1.md", ["references"])
        assert resolved == skill_structure / "references" / "api" / "v1.md"
        
        # Path with current directory references (but no ..)
        resolved = resolver.resolve("references/./api/./v1.md", ["references"])
        assert resolved == skill_structure / "references" / "api" / "v1.md"
    
    def test_concurrent_resolvers(self, skill_structure, tmp_path):
        """Test multiple resolvers for different skills work independently."""
        # Create another skill
        other_skill = tmp_path / "other-skill"
        other_skill.mkdir()
        (other_skill / "references").mkdir()
        (other_skill / "references" / "other.md").write_text("Other")
        
        resolver1 = PathResolver(skill_structure)
        resolver2 = PathResolver(other_skill)
        
        # Each resolver should only access its own skill
        path1 = resolver1.resolve("references/README.md", ["references"])
        assert path1.is_relative_to(skill_structure)
        
        path2 = resolver2.resolve("references/other.md", ["references"])
        assert path2.is_relative_to(other_skill)
        
        # Resolver 1 cannot access resolver 2's files
        with pytest.raises(PathTraversalError):
            # Try to construct a path that would escape
            resolver1.resolve("../other-skill/references/other.md", ["references"])
