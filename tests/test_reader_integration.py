"""Integration tests for ResourceReader with PathResolver."""

import pytest
from pathlib import Path
from agent_skills.resources.reader import ResourceReader
from agent_skills.resources.resolver import PathResolver
from agent_skills.models import ResourcePolicy
from agent_skills.exceptions import PathTraversalError, PolicyViolationError, ResourceTooLargeError


@pytest.fixture
def skill_directory(tmp_path):
    """Create a mock skill directory structure."""
    skill_root = tmp_path / "test-skill"
    skill_root.mkdir()
    
    # Create references directory with files
    references = skill_root / "references"
    references.mkdir()
    (references / "api-docs.md").write_text("# API Documentation\n\nThis is the API.", encoding='utf-8')
    (references / "examples.json").write_text('{"example": "data"}', encoding='utf-8')
    
    # Create assets directory with files
    assets = skill_root / "assets"
    assets.mkdir()
    (assets / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (assets / "data.csv").write_text("col1,col2\n1,2\n3,4", encoding='utf-8')
    
    # Create a file outside allowed directories
    (skill_root / "SKILL.md").write_text("---\nname: test\n---\n# Test", encoding='utf-8')
    
    return skill_root


@pytest.fixture
def resolver(skill_directory):
    """Create a PathResolver for the skill directory."""
    return PathResolver(skill_directory)


@pytest.fixture
def reader():
    """Create a ResourceReader with default policy."""
    return ResourceReader(ResourcePolicy())


class TestIntegratedPathResolutionAndReading:
    """Tests for integrated path resolution and file reading."""
    
    def test_read_reference_file(self, skill_directory, resolver, reader):
        """Test reading a file from references directory."""
        # Resolve path
        resolved_path = resolver.resolve("references/api-docs.md", ["references"])
        
        # Read file
        content, truncated = reader.read_text(resolved_path)
        
        assert "API Documentation" in content
        assert truncated is False
    
    def test_read_asset_file(self, skill_directory, resolver, reader):
        """Test reading a binary file from assets directory."""
        # Resolve path
        resolved_path = resolver.resolve("assets/image.png", ["assets"])
        
        # Read file
        content, truncated = reader.read_binary(resolved_path)
        
        assert content.startswith(b"\x89PNG")
        assert truncated is False
    
    def test_read_multiple_files_tracks_session_bytes(self, skill_directory, resolver, reader):
        """Test that reading multiple files tracks total session bytes."""
        # Read first file
        path1 = resolver.resolve("references/api-docs.md", ["references"])
        content1, _ = reader.read_text(path1)
        bytes_after_first = reader.get_session_bytes_read()
        
        # Read second file
        path2 = resolver.resolve("references/examples.json", ["references"])
        content2, _ = reader.read_text(path2)
        bytes_after_second = reader.get_session_bytes_read()
        
        # Verify session tracking
        assert bytes_after_second > bytes_after_first
        expected_total = len(content1.encode('utf-8')) + len(content2.encode('utf-8'))
        assert bytes_after_second == expected_total
    
    def test_path_traversal_blocked(self, skill_directory, resolver, reader):
        """Test that path traversal attempts are blocked."""
        # Attempt path traversal
        with pytest.raises(PathTraversalError):
            resolver.resolve("references/../../etc/passwd", ["references"])
    
    def test_access_outside_allowed_dirs_blocked(self, skill_directory, resolver, reader):
        """Test that accessing files outside allowed directories is blocked."""
        # Attempt to access SKILL.md when only references is allowed
        with pytest.raises(PolicyViolationError):
            resolver.resolve("SKILL.md", ["references"])
    
    def test_read_with_size_limit(self, skill_directory, resolver):
        """Test reading a file with size limits enforced."""
        # Create a large file
        large_file = skill_directory / "references" / "large.md"
        large_content = "A" * 300_000  # 300KB
        large_file.write_text(large_content, encoding='utf-8')
        
        # Create reader with strict policy
        strict_reader = ResourceReader(ResourcePolicy(max_file_bytes=100_000))
        
        # Resolve and read
        resolved_path = resolver.resolve("references/large.md", ["references"])
        content, truncated = strict_reader.read_text(resolved_path)
        
        assert len(content) <= 100_000
        assert truncated is True
    
    def test_session_limit_across_multiple_files(self, skill_directory, resolver):
        """Test that session limit is enforced across multiple file reads."""
        # Create reader with strict session limit
        strict_reader = ResourceReader(ResourcePolicy(
            max_file_bytes=50_000,
            max_total_bytes_per_session=100_000
        ))
        
        # Create multiple files
        for i in range(5):
            file_path = skill_directory / "references" / f"file{i}.md"
            file_path.write_text("X" * 30_000, encoding='utf-8')  # 30KB each
        
        # Read files until we hit session limit
        files_read = 0
        try:
            for i in range(5):
                path = resolver.resolve(f"references/file{i}.md", ["references"])
                strict_reader.read_text(path)
                files_read += 1
        except ResourceTooLargeError:
            pass
        
        # Should have read 3 files (90KB) before hitting 100KB limit on the 4th read
        # The 4th file would push us over 100KB, so we should have successfully read 3
        assert files_read >= 3
        assert strict_reader.get_session_bytes_read() <= 100_000


class TestIntegratedSecurityScenarios:
    """Tests for security scenarios with integrated components."""
    
    def test_cannot_read_outside_skill_root(self, skill_directory, resolver, reader):
        """Test that files outside skill root cannot be accessed."""
        # Create a file outside skill root
        outside_file = skill_directory.parent / "secret.txt"
        outside_file.write_text("secret data", encoding='utf-8')
        
        # Attempt to access it
        with pytest.raises(PathTraversalError):
            resolver.resolve("../secret.txt", ["references"])
    
    def test_absolute_paths_blocked(self, skill_directory, resolver, reader):
        """Test that absolute paths are blocked."""
        with pytest.raises(PathTraversalError):
            resolver.resolve("/etc/passwd", ["references"])
    
    def test_symlink_traversal_blocked(self, skill_directory, resolver, reader):
        """Test that symlinks cannot be used for path traversal."""
        # Create a symlink pointing outside skill root
        outside_dir = skill_directory.parent / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("secret", encoding='utf-8')
        
        # Create symlink in references
        references = skill_directory / "references"
        symlink = references / "link"
        try:
            symlink.symlink_to(outside_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this system")
        
        # Attempt to resolve the symlink path - should be blocked
        # because the resolved path escapes the skill root
        with pytest.raises(PathTraversalError) as exc_info:
            resolver.resolve("references/link/secret.txt", ["references"])
        
        assert "Path escapes skill root" in str(exc_info.value)


class TestIntegratedRealWorldScenarios:
    """Tests for real-world usage scenarios."""
    
    def test_read_skill_documentation(self, skill_directory, resolver, reader):
        """Test reading skill documentation files."""
        # Read API docs
        api_path = resolver.resolve("references/api-docs.md", ["references"])
        api_content, _ = reader.read_text(api_path)
        assert "API Documentation" in api_content
        
        # Read examples
        examples_path = resolver.resolve("references/examples.json", ["references"])
        examples_content, _ = reader.read_text(examples_path)
        assert "example" in examples_content
        
        # Verify session tracking
        assert reader.get_session_bytes_read() > 0
    
    def test_read_skill_assets(self, skill_directory, resolver, reader):
        """Test reading skill asset files."""
        # Read image
        image_path = resolver.resolve("assets/image.png", ["assets"])
        image_content, _ = reader.read_binary(image_path)
        assert len(image_content) > 0
        
        # Read CSV data
        csv_path = resolver.resolve("assets/data.csv", ["assets"])
        csv_content, _ = reader.read_text(csv_path)
        assert "col1,col2" in csv_content
    
    def test_compute_hash_of_read_content(self, skill_directory, resolver, reader):
        """Test computing hash of read content for audit logging."""
        # Read file
        path = resolver.resolve("references/api-docs.md", ["references"])
        content, _ = reader.read_text(path)
        
        # Compute hash
        hash_value = reader.compute_sha256(content)
        
        assert len(hash_value) == 64  # SHA256 is 64 hex characters
        assert hash_value.isalnum()
    
    def test_multiple_readers_independent_sessions(self, skill_directory, resolver):
        """Test that multiple readers have independent session tracking."""
        reader1 = ResourceReader(ResourcePolicy())
        reader2 = ResourceReader(ResourcePolicy())
        
        # Read with first reader
        path = resolver.resolve("references/api-docs.md", ["references"])
        reader1.read_text(path)
        bytes1 = reader1.get_session_bytes_read()
        
        # Second reader should have independent counter
        assert reader2.get_session_bytes_read() == 0
        
        # Read with second reader
        reader2.read_text(path)
        bytes2 = reader2.get_session_bytes_read()
        
        # Both should have read the same amount
        assert bytes1 == bytes2
        assert bytes1 > 0
