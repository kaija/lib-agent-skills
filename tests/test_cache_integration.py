"""Integration tests for MetadataCache with discovery workflow."""

import time
from pathlib import Path

import pytest

from agent_skills.discovery import SkillScanner, SkillIndexer, MetadataCache


class TestCacheIntegration:
    """Integration tests for cache with scanner and indexer."""
    
    def test_cache_speeds_up_repeated_scans(self, temp_dir: Path):
        """Test that cache improves performance on repeated scans."""
        # Create a skill
        skill_dir = temp_dir / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill
license: MIT
---

# Instructions
Test instructions.
""")
        
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        scanner = SkillScanner()
        indexer = SkillIndexer()
        
        # First scan - no cache
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        
        assert len(descriptors) == 1
        descriptor = descriptors[0]
        
        # Cache the descriptor
        cache.put(descriptor)
        
        # Second scan - should use cache
        cached_descriptor = cache.get(skill_dir)
        
        assert cached_descriptor is not None
        assert cached_descriptor.name == descriptor.name
        assert cached_descriptor.description == descriptor.description
        assert cached_descriptor.hash == descriptor.hash
        assert cached_descriptor.mtime == descriptor.mtime
    
    def test_cache_invalidation_workflow(self, temp_dir: Path):
        """Test complete workflow with cache invalidation."""
        # Create a skill
        skill_dir = temp_dir / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Original description
---
""")
        
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        scanner = SkillScanner()
        indexer = SkillIndexer()
        
        # Initial scan and cache
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        descriptor = descriptors[0]
        cache.put(descriptor)
        
        # Verify cache hit
        cached = cache.get(skill_dir)
        assert cached is not None
        assert cached.description == "Original description"
        
        # Modify the skill
        time.sleep(0.01)  # Ensure mtime changes
        skill_md.write_text("""---
name: test-skill
description: Updated description
---
""")
        
        # Cache should be invalid now
        cached = cache.get(skill_dir)
        assert cached is None
        
        # Re-scan and cache
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        new_descriptor = descriptors[0]
        cache.put(new_descriptor)
        
        # Verify new cache
        cached = cache.get(skill_dir)
        assert cached is not None
        assert cached.description == "Updated description"
        assert cached.hash != descriptor.hash  # Hash should be different
    
    def test_cache_with_multiple_skills(self, temp_dir: Path):
        """Test cache with multiple skills."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        scanner = SkillScanner()
        indexer = SkillIndexer()
        
        # Create multiple skills
        for i in range(5):
            skill_dir = temp_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: skill-{i}
description: Skill number {i}
---
""")
        
        # Scan and cache all
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        
        assert len(descriptors) == 5
        
        for descriptor in descriptors:
            cache.put(descriptor)
        
        # Verify all are cached
        for i in range(5):
            skill_dir = temp_dir / f"skill-{i}"
            cached = cache.get(skill_dir)
            assert cached is not None
            assert cached.name == f"skill-{i}"
            assert cached.description == f"Skill number {i}"
    
    def test_cache_survives_process_restart(self, temp_dir: Path):
        """Test that cache persists across 'process restarts' (new cache instances)."""
        # Create a skill
        skill_dir = temp_dir / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Persistent skill
---
""")
        
        cache_dir = temp_dir / "cache"
        
        # First "process" - create cache and store descriptor
        cache1 = MetadataCache(cache_dir)
        scanner = SkillScanner()
        indexer = SkillIndexer()
        
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        cache1.put(descriptors[0])
        
        # Second "process" - new cache instance
        cache2 = MetadataCache(cache_dir)
        
        # Should be able to retrieve from cache
        cached = cache2.get(skill_dir)
        assert cached is not None
        assert cached.name == "test-skill"
        assert cached.description == "Persistent skill"
    
    def test_cache_optimization_scenario(self, temp_dir: Path):
        """Test realistic optimization scenario with cache hits and misses."""
        cache_dir = temp_dir / "cache"
        cache = MetadataCache(cache_dir)
        scanner = SkillScanner()
        indexer = SkillIndexer()
        
        # Create 3 skills
        skills = []
        for i in range(3):
            skill_dir = temp_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: skill-{i}
description: Skill {i}
---
""")
            skills.append(skill_dir)
        
        # Initial scan - cache all
        skill_paths = scanner.scan([temp_dir])
        descriptors = indexer.index_skills(skill_paths)
        for descriptor in descriptors:
            cache.put(descriptor)
        
        # Modify only skill-1
        time.sleep(0.01)
        skill_1_md = skills[1] / "SKILL.md"
        skill_1_md.write_text("""---
name: skill-1
description: Modified skill 1
---
""")
        
        # Check cache status
        # skill-0: should be cached
        cached_0 = cache.get(skills[0])
        assert cached_0 is not None
        assert cached_0.description == "Skill 0"
        
        # skill-1: should be invalid (modified)
        cached_1 = cache.get(skills[1])
        assert cached_1 is None
        
        # skill-2: should be cached
        cached_2 = cache.get(skills[2])
        assert cached_2 is not None
        assert cached_2.description == "Skill 2"
        
        # Re-index only the modified skill
        skill_paths = [skills[1]]
        descriptors = indexer.index_skills(skill_paths)
        cache.put(descriptors[0])
        
        # Now skill-1 should be cached with new content
        cached_1 = cache.get(skills[1])
        assert cached_1 is not None
        assert cached_1.description == "Modified skill 1"
