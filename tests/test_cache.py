"""Unit tests for MetadataCache."""

import json
import time
from pathlib import Path

import pytest

from agent_skills.discovery import MetadataCache
from agent_skills.models import SkillDescriptor


class TestMetadataCache:
    """Test suite for MetadataCache."""
    
    def test_cache_initialization(self, temp_dir: Path):
        """Test that cache directory is created on initialization."""
        cache_dir = temp_dir / "cache"
        assert not cache_dir.exists()
        
        cache = MetadataCache(cache_dir)
        
        assert cache_dir.exists()
        assert cache_dir.is_dir()
    
    def test_cache_put_and_get(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test storing and retrieving a descriptor from cache."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create a descriptor
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=skill_root,
            license="MIT",
            hash="abc123",
            mtime=sample_skill_md.stat().st_mtime,
        )
        
        # Store in cache
        cache.put(descriptor)
        
        # Retrieve from cache
        cached = cache.get(skill_root)
        
        assert cached is not None
        assert cached.name == descriptor.name
        assert cached.description == descriptor.description
        assert cached.path == descriptor.path
        assert cached.license == descriptor.license
        assert cached.hash == descriptor.hash
        assert cached.mtime == descriptor.mtime
    
    def test_cache_miss_returns_none(self, temp_dir: Path, skill_root: Path):
        """Test that cache miss returns None."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Try to get non-existent cache entry
        cached = cache.get(skill_root)
        
        assert cached is None
    
    def test_cache_invalidation_on_mtime_change(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that cache is invalidated when file mtime changes."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create and cache a descriptor
        original_mtime = sample_skill_md.stat().st_mtime
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=skill_root,
            hash="abc123",
            mtime=original_mtime,
        )
        cache.put(descriptor)
        
        # Verify it's cached
        assert cache.get(skill_root) is not None
        
        # Modify the file to change mtime
        time.sleep(0.01)  # Ensure mtime changes
        sample_skill_md.write_text(sample_skill_md.read_text() + "\n# Modified")
        
        # Cache should be invalid now
        cached = cache.get(skill_root)
        assert cached is None
    
    def test_cache_invalidate_method(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test explicit cache invalidation."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create and cache a descriptor
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=skill_root,
            hash="abc123",
            mtime=sample_skill_md.stat().st_mtime,
        )
        cache.put(descriptor)
        
        # Verify it's cached
        assert cache.get(skill_root) is not None
        
        # Invalidate cache
        cache.invalidate(skill_root)
        
        # Cache should be gone
        assert cache.get(skill_root) is None
    
    def test_cache_clear_all(self, temp_dir: Path):
        """Test clearing all cache entries."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create multiple skill directories and cache them
        skills = []
        for i in range(3):
            skill_dir = temp_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"---\nname: skill-{i}\ndescription: Test\n---\n")
            
            descriptor = SkillDescriptor(
                name=f"skill-{i}",
                description="Test",
                path=skill_dir,
                hash=f"hash{i}",
                mtime=skill_md.stat().st_mtime,
            )
            cache.put(descriptor)
            skills.append(skill_dir)
        
        # Verify all are cached
        for skill_dir in skills:
            assert cache.get(skill_dir) is not None
        
        # Clear cache
        cache.clear()
        
        # All should be gone
        for skill_dir in skills:
            assert cache.get(skill_dir) is None
    
    def test_cache_handles_missing_skill_md(self, temp_dir: Path, skill_root: Path):
        """Test that cache returns None if SKILL.md doesn't exist."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create a descriptor for a skill without SKILL.md
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=skill_root,
            hash="abc123",
            mtime=time.time(),
        )
        cache.put(descriptor)
        
        # Try to get it (SKILL.md doesn't exist)
        cached = cache.get(skill_root)
        
        assert cached is None
    
    def test_cache_handles_corrupted_cache_file(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that corrupted cache files are handled gracefully."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create a descriptor
        descriptor = SkillDescriptor(
            name="test-skill",
            description="A test skill",
            path=skill_root,
            hash="abc123",
            mtime=sample_skill_md.stat().st_mtime,
        )
        cache.put(descriptor)
        
        # Corrupt the cache file
        cache_path = cache._get_cache_path(skill_root)
        cache_path.write_text("{ invalid json }")
        
        # Should return None and not raise an exception
        cached = cache.get(skill_root)
        assert cached is None
        
        # Cache file should be removed
        assert not cache_path.exists()
    
    def test_cache_path_hashing(self, temp_dir: Path):
        """Test that cache uses path hashing for filenames."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        skill_dir = temp_dir / "my-skill"
        skill_dir.mkdir()
        
        cache_path = cache._get_cache_path(skill_dir)
        
        # Cache path should be in cache_dir
        assert cache_path.parent == cache_dir
        
        # Cache filename should be a hash with .json extension
        assert cache_path.suffix == ".json"
        assert len(cache_path.stem) == 64  # SHA256 hex length
    
    def test_cache_serialization_preserves_all_fields(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that all descriptor fields are preserved through cache."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create a descriptor with all fields populated
        descriptor = SkillDescriptor(
            name="full-skill",
            description="A skill with all fields",
            path=skill_root,
            license="Apache-2.0",
            compatibility={"frameworks": ["langchain", "adk"]},
            metadata={"version": "2.0.0", "author": "Test"},
            allowed_tools=["skills.read", "skills.run"],
            hash="def456",
            mtime=sample_skill_md.stat().st_mtime,
        )
        
        # Store and retrieve
        cache.put(descriptor)
        cached = cache.get(skill_root)
        
        assert cached is not None
        assert cached.name == descriptor.name
        assert cached.description == descriptor.description
        assert cached.path == descriptor.path
        assert cached.license == descriptor.license
        assert cached.compatibility == descriptor.compatibility
        assert cached.metadata == descriptor.metadata
        assert cached.allowed_tools == descriptor.allowed_tools
        assert cached.hash == descriptor.hash
        assert cached.mtime == descriptor.mtime
    
    def test_cache_handles_none_optional_fields(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that cache handles None values for optional fields."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create a descriptor with minimal fields
        descriptor = SkillDescriptor(
            name="minimal-skill",
            description="Minimal descriptor",
            path=skill_root,
            license=None,
            compatibility=None,
            metadata=None,
            allowed_tools=None,
            hash="",
            mtime=sample_skill_md.stat().st_mtime,
        )
        
        # Store and retrieve
        cache.put(descriptor)
        cached = cache.get(skill_root)
        
        assert cached is not None
        assert cached.name == descriptor.name
        assert cached.license is None
        assert cached.compatibility is None
        assert cached.metadata is None
        assert cached.allowed_tools is None
    
    def test_cache_handles_unwritable_directory(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that cache handles unwritable cache directory gracefully."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        descriptor = SkillDescriptor(
            name="test-skill",
            description="Test",
            path=skill_root,
            hash="abc123",
            mtime=sample_skill_md.stat().st_mtime,
        )
        
        # Make cache directory read-only (on Unix systems)
        import os
        if os.name != 'nt':  # Skip on Windows
            cache_dir.chmod(0o444)
            
            # Should not raise an exception
            cache.put(descriptor)
            
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)
    
    def test_cache_with_different_skill_paths(self, temp_dir: Path):
        """Test that cache correctly handles different skill paths."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Create two different skills
        skill1 = temp_dir / "skill-1"
        skill1.mkdir()
        skill1_md = skill1 / "SKILL.md"
        skill1_md.write_text("---\nname: skill-1\ndescription: First\n---\n")
        
        skill2 = temp_dir / "skill-2"
        skill2.mkdir()
        skill2_md = skill2 / "SKILL.md"
        skill2_md.write_text("---\nname: skill-2\ndescription: Second\n---\n")
        
        # Cache both
        desc1 = SkillDescriptor(
            name="skill-1",
            description="First",
            path=skill1,
            hash="hash1",
            mtime=skill1_md.stat().st_mtime,
        )
        desc2 = SkillDescriptor(
            name="skill-2",
            description="Second",
            path=skill2,
            hash="hash2",
            mtime=skill2_md.stat().st_mtime,
        )
        
        cache.put(desc1)
        cache.put(desc2)
        
        # Retrieve both
        cached1 = cache.get(skill1)
        cached2 = cache.get(skill2)
        
        assert cached1 is not None
        assert cached2 is not None
        assert cached1.name == "skill-1"
        assert cached2.name == "skill-2"
        assert cached1.hash == "hash1"
        assert cached2.hash == "hash2"
    
    def test_cache_json_format(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that cache files are valid JSON."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        descriptor = SkillDescriptor(
            name="test-skill",
            description="Test",
            path=skill_root,
            hash="abc123",
            mtime=sample_skill_md.stat().st_mtime,
        )
        
        cache.put(descriptor)
        
        # Read cache file directly
        cache_path = cache._get_cache_path(skill_root)
        with open(cache_path, 'r') as f:
            data = json.load(f)
        
        # Verify it's valid JSON with expected fields
        assert data['name'] == "test-skill"
        assert data['description'] == "Test"
        assert data['hash'] == "abc123"
        assert 'path' in data
        assert 'mtime' in data
    
    def test_cache_mtime_tolerance(self, temp_dir: Path, skill_root: Path, sample_skill_md: Path):
        """Test that cache allows small mtime differences due to float precision."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Get actual mtime
        actual_mtime = sample_skill_md.stat().st_mtime
        
        # Create descriptor with slightly different mtime (within tolerance)
        descriptor = SkillDescriptor(
            name="test-skill",
            description="Test",
            path=skill_root,
            hash="abc123",
            mtime=actual_mtime + 0.0001,  # Very small difference
        )
        
        cache.put(descriptor)
        
        # Should still be valid
        cached = cache.get(skill_root)
        assert cached is not None
    
    def test_cache_invalidate_nonexistent(self, temp_dir: Path, skill_root: Path):
        """Test that invalidating non-existent cache doesn't raise error."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Should not raise an exception
        cache.invalidate(skill_root)
    
    def test_cache_clear_empty_cache(self, temp_dir: Path):
        """Test that clearing empty cache doesn't raise error."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        
        # Should not raise an exception
        cache.clear()
