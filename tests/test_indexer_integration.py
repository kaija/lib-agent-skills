"""Integration tests for skill discovery and indexing workflow."""

from pathlib import Path

import pytest

from agent_skills.discovery import SkillScanner, SkillIndexer
from agent_skills.models import SkillDescriptor


def test_complete_discovery_and_indexing_workflow(temp_dir: Path):
    """Test the complete workflow from scanning to indexing."""
    # Create a realistic skill structure
    skill1 = temp_dir / "data-processor"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: data-processor
description: Process CSV and JSON data files
license: MIT
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Data Team
  version: 2.1.0
  tags: ["data", "processing", "csv", "json"]
allowed_tools:
  - skills.read
  - skills.run
---

# Data Processor Skill

This skill helps you process various data formats.

## Usage

1. Read the API documentation from references/
2. Execute the processing script
3. Verify the output
""")
    
    # Create references directory
    refs = skill1 / "references"
    refs.mkdir()
    (refs / "api-docs.md").write_text("# API Documentation\n\nDetailed API docs here.")
    
    # Create scripts directory
    scripts = skill1 / "scripts"
    scripts.mkdir()
    (scripts / "process.py").write_text("#!/usr/bin/env python3\nprint('Processing...')")
    
    # Create another skill
    skill2 = temp_dir / "api-client"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: api-client
description: Make HTTP requests to external APIs
license: Apache-2.0
---

# API Client Skill

Use this skill to interact with REST APIs.
""")
    
    # Step 1: Scan for skills
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    assert len(skill_paths) == 2
    
    # Step 2: Index the discovered skills
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    assert len(descriptors) == 2
    
    # Verify the descriptors
    descriptor_map = {d.name: d for d in descriptors}
    
    # Check data-processor
    data_proc = descriptor_map["data-processor"]
    assert data_proc.description == "Process CSV and JSON data files"
    assert data_proc.license == "MIT"
    assert data_proc.compatibility["frameworks"] == ["langchain", "adk"]
    assert data_proc.metadata["author"] == "Data Team"
    assert data_proc.allowed_tools == ["skills.read", "skills.run"]
    assert data_proc.hash != ""
    assert data_proc.mtime > 0
    assert data_proc.path == skill1
    
    # Check api-client
    api_client = descriptor_map["api-client"]
    assert api_client.description == "Make HTTP requests to external APIs"
    assert api_client.license == "Apache-2.0"
    assert api_client.compatibility is None
    assert api_client.metadata is None
    assert api_client.allowed_tools is None
    assert api_client.hash != ""
    assert api_client.mtime > 0
    assert api_client.path == skill2


def test_requirement_2_2_parse_frontmatter_to_create_descriptor(temp_dir: Path):
    """Test Requirement 2.2: Parse frontmatter to create SkillDescriptor."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
license: MIT
---

# Instructions
""")
    
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    # Should create a SkillDescriptor
    assert len(descriptors) == 1
    assert isinstance(descriptors[0], SkillDescriptor)
    assert descriptors[0].name == "test-skill"
    assert descriptors[0].description == "A test skill"


def test_requirement_2_3_return_list_of_descriptors(temp_dir: Path):
    """Test Requirement 2.3: Return list of all discovered SkillDescriptor objects."""
    # Create multiple skills
    for i in range(5):
        skill_dir = temp_dir / f"skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: skill-{i}
description: Skill number {i}
---
""")
    
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    # Should return a list of all descriptors
    assert len(descriptors) == 5
    assert all(isinstance(d, SkillDescriptor) for d in descriptors)


def test_indexing_with_nested_skills(temp_dir: Path):
    """Test indexing skills in nested directory structures."""
    # Create nested structure
    categories = ["data", "api", "ml"]
    for category in categories:
        category_dir = temp_dir / category
        category_dir.mkdir()
        
        for i in range(2):
            skill_dir = category_dir / f"{category}-skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"""---
name: {category}-skill-{i}
description: {category.upper()} skill number {i}
---
""")
    
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    # Should find all 6 skills (3 categories × 2 skills each)
    assert len(descriptors) == 6
    
    # Verify we have skills from all categories
    names = {d.name for d in descriptors}
    assert "data-skill-0" in names
    assert "api-skill-1" in names
    assert "ml-skill-0" in names


def test_indexing_with_multiple_roots(temp_dir: Path):
    """Test indexing skills from multiple root directories."""
    # Create two separate root directories
    root1 = temp_dir / "root1"
    root1.mkdir()
    skill1 = root1 / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: skill-1
description: Skill from root 1
---
""")
    
    root2 = temp_dir / "root2"
    root2.mkdir()
    skill2 = root2 / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: skill-2
description: Skill from root 2
---
""")
    
    # Scan both roots
    scanner = SkillScanner()
    skill_paths = scanner.scan([root1, root2])
    
    # Index all discovered skills
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    assert len(descriptors) == 2
    names = {d.name for d in descriptors}
    assert names == {"skill-1", "skill-2"}


def test_indexing_handles_mixed_valid_and_invalid_skills(temp_dir: Path, capsys):
    """Test that indexing continues when some skills are invalid."""
    # Create valid skills
    for i in [1, 3, 5]:
        skill_dir = temp_dir / f"valid-skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: valid-skill-{i}
description: Valid skill {i}
---
""")
    
    # Create invalid skills (missing description)
    for i in [2, 4]:
        skill_dir = temp_dir / f"invalid-skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: invalid-skill-{i}
---
""")
    
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    # Should only have the 3 valid skills
    assert len(descriptors) == 3
    names = {d.name for d in descriptors}
    assert names == {"valid-skill-1", "valid-skill-3", "valid-skill-5"}
    
    # Should have printed warnings for invalid skills
    captured = capsys.readouterr()
    assert "invalid-skill-2" in captured.out
    assert "invalid-skill-4" in captured.out


def test_descriptor_serialization_after_indexing(temp_dir: Path):
    """Test that descriptors can be serialized after indexing."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
license: MIT
metadata:
  version: 1.0.0
---
""")
    
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    # Serialize and deserialize
    descriptor = descriptors[0]
    serialized = descriptor.to_dict()
    deserialized = SkillDescriptor.from_dict(serialized)
    
    # Should be equivalent
    assert deserialized.name == descriptor.name
    assert deserialized.description == descriptor.description
    assert deserialized.license == descriptor.license
    assert deserialized.metadata == descriptor.metadata
    assert deserialized.hash == descriptor.hash
    assert deserialized.mtime == descriptor.mtime
    assert deserialized.path == descriptor.path


def test_indexing_performance_with_many_skills(temp_dir: Path):
    """Test that indexing performs well with many skills."""
    import time
    
    # Create 50 skills
    num_skills = 50
    for i in range(num_skills):
        skill_dir = temp_dir / f"skill-{i:03d}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: skill-{i:03d}
description: Skill number {i}
license: MIT
metadata:
  version: 1.0.0
  index: {i}
---

# Skill {i}

This is skill number {i}.
""")
    
    scanner = SkillScanner()
    indexer = SkillIndexer()
    
    # Measure scanning time
    start = time.time()
    skill_paths = scanner.scan([temp_dir])
    scan_time = time.time() - start
    
    # Measure indexing time
    start = time.time()
    descriptors = indexer.index_skills(skill_paths)
    index_time = time.time() - start
    
    # Verify results
    assert len(descriptors) == num_skills
    
    # Performance check: should complete in reasonable time
    # (This is a loose check - adjust if needed based on hardware)
    assert scan_time < 1.0, f"Scanning took {scan_time:.2f}s, expected < 1.0s"
    assert index_time < 1.0, f"Indexing took {index_time:.2f}s, expected < 1.0s"
    
    print(f"\nPerformance: Scanned {num_skills} skills in {scan_time:.3f}s")
    print(f"Performance: Indexed {num_skills} skills in {index_time:.3f}s")
