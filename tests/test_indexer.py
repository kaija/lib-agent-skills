"""Unit tests for SkillIndexer."""

from pathlib import Path

import pytest

from agent_skills.discovery import SkillIndexer, SkillScanner
from agent_skills.exceptions import SkillParseError
from agent_skills.models import SkillDescriptor


def test_indexer_creates_descriptor_from_valid_skill(temp_dir: Path):
    """Test that indexer creates a SkillDescriptor from a valid skill."""
    # Create a valid skill
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
license: MIT
---

# Instructions
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.name == "test-skill"
    assert descriptor.description == "A test skill"
    assert descriptor.license == "MIT"
    assert descriptor.path == skill_dir
    assert descriptor.hash != ""  # Should have a hash
    assert descriptor.mtime > 0  # Should have a modification time


def test_indexer_creates_descriptors_for_multiple_skills(temp_dir: Path):
    """Test that indexer creates descriptors for multiple skills."""
    # Create multiple skills
    skill1 = temp_dir / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: skill-1
description: First skill
---
""")
    
    skill2 = temp_dir / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: skill-2
description: Second skill
---
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill1, skill2])
    
    assert len(descriptors) == 2
    names = {d.name for d in descriptors}
    assert names == {"skill-1", "skill-2"}


def test_indexer_includes_all_frontmatter_fields(temp_dir: Path):
    """Test that indexer includes all frontmatter fields in the descriptor."""
    skill_dir = temp_dir / "full-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: full-skill
description: A skill with all fields
license: Apache-2.0
compatibility:
  frameworks: ["langchain", "adk"]
  python: ">=3.10"
metadata:
  author: Test Author
  version: 1.0.0
  tags: ["test", "example"]
allowed_tools:
  - skills.read
  - skills.run
---

# Instructions
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.name == "full-skill"
    assert descriptor.description == "A skill with all fields"
    assert descriptor.license == "Apache-2.0"
    assert descriptor.compatibility == {
        "frameworks": ["langchain", "adk"],
        "python": ">=3.10"
    }
    assert descriptor.metadata == {
        "author": "Test Author",
        "version": "1.0.0",
        "tags": ["test", "example"]
    }
    assert descriptor.allowed_tools == ["skills.read", "skills.run"]


def test_indexer_handles_minimal_frontmatter(temp_dir: Path):
    """Test that indexer handles skills with only required fields."""
    skill_dir = temp_dir / "minimal-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: minimal-skill
description: Minimal skill with only required fields
---

# Instructions
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.name == "minimal-skill"
    assert descriptor.description == "Minimal skill with only required fields"
    assert descriptor.license is None
    assert descriptor.compatibility is None
    assert descriptor.metadata is None
    assert descriptor.allowed_tools is None


def test_indexer_handles_parsing_errors_gracefully(temp_dir: Path, capsys):
    """Test that indexer handles parsing errors gracefully and continues."""
    # Create a valid skill
    valid_skill = temp_dir / "valid-skill"
    valid_skill.mkdir()
    (valid_skill / "SKILL.md").write_text("""---
name: valid-skill
description: A valid skill
---
""")
    
    # Create an invalid skill (missing required field)
    invalid_skill = temp_dir / "invalid-skill"
    invalid_skill.mkdir()
    (invalid_skill / "SKILL.md").write_text("""---
name: invalid-skill
---
""")
    
    # Create another valid skill
    another_valid = temp_dir / "another-valid"
    another_valid.mkdir()
    (another_valid / "SKILL.md").write_text("""---
name: another-valid
description: Another valid skill
---
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([valid_skill, invalid_skill, another_valid])
    
    # Should have 2 valid descriptors
    assert len(descriptors) == 2
    names = {d.name for d in descriptors}
    assert names == {"valid-skill", "another-valid"}
    
    # Should have printed a warning
    captured = capsys.readouterr()
    assert "Warning: Failed to parse skill" in captured.out
    assert "invalid-skill" in captured.out


def test_indexer_handles_missing_skill_md(temp_dir: Path, capsys):
    """Test that indexer handles missing SKILL.md files gracefully."""
    # Create a directory without SKILL.md
    skill_dir = temp_dir / "no-skill-md"
    skill_dir.mkdir()
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    # Should return empty list
    assert len(descriptors) == 0
    
    # Should have printed a warning
    captured = capsys.readouterr()
    assert "Warning: Failed to parse skill" in captured.out


def test_indexer_handles_invalid_yaml(temp_dir: Path, capsys):
    """Test that indexer handles invalid YAML gracefully."""
    skill_dir = temp_dir / "invalid-yaml"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: invalid-yaml
description: [unclosed bracket
---
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    # Should return empty list
    assert len(descriptors) == 0
    
    # Should have printed a warning
    captured = capsys.readouterr()
    assert "Warning: Failed to parse skill" in captured.out


def test_indexer_computes_hash_for_each_skill(temp_dir: Path):
    """Test that indexer computes a unique hash for each skill's frontmatter."""
    skill1 = temp_dir / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: skill-1
description: First skill
---
""")
    
    skill2 = temp_dir / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: skill-2
description: Second skill
---
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill1, skill2])
    
    assert len(descriptors) == 2
    # Hashes should be different for different frontmatter
    assert descriptors[0].hash != descriptors[1].hash
    # Hashes should not be empty
    assert descriptors[0].hash != ""
    assert descriptors[1].hash != ""


def test_indexer_sets_modification_time(temp_dir: Path):
    """Test that indexer sets the modification time for each skill."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill
---
""")
    
    # Get the actual mtime
    expected_mtime = skill_md.stat().st_mtime
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    assert len(descriptors) == 1
    assert descriptors[0].mtime == expected_mtime


def test_indexer_integration_with_scanner(temp_dir: Path):
    """Test that indexer works correctly with scanner output."""
    # Create multiple skills
    skill1 = temp_dir / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: skill-1
description: First skill
---
""")
    
    skill2 = temp_dir / "nested" / "skill-2"
    skill2.mkdir(parents=True)
    (skill2 / "SKILL.md").write_text("""---
name: skill-2
description: Second skill
---
""")
    
    # Use scanner to find skills
    scanner = SkillScanner()
    skill_paths = scanner.scan([temp_dir])
    
    # Use indexer to create descriptors
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skill_paths)
    
    assert len(descriptors) == 2
    names = {d.name for d in descriptors}
    assert names == {"skill-1", "skill-2"}


def test_indexer_handles_empty_skill_list():
    """Test that indexer handles empty skill list."""
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([])
    
    assert len(descriptors) == 0


def test_indexer_descriptor_has_correct_path(temp_dir: Path):
    """Test that descriptor has the correct path to the skill directory."""
    skill_dir = temp_dir / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: Test skill
---
""")
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills([skill_dir])
    
    assert len(descriptors) == 1
    assert descriptors[0].path == skill_dir
    assert descriptors[0].path.is_absolute()


def test_indexer_handles_unexpected_errors(temp_dir: Path, capsys, monkeypatch):
    """Test that indexer handles unexpected errors gracefully."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: Test skill
---
""")
    
    # Mock the parser to raise an unexpected error
    def mock_parse(self, path):
        raise RuntimeError("Unexpected error")
    
    indexer = SkillIndexer()
    monkeypatch.setattr(indexer.parser, "parse", mock_parse)
    
    descriptors = indexer.index_skills([skill_dir])
    
    # Should return empty list
    assert len(descriptors) == 0
    
    # Should have printed a warning
    captured = capsys.readouterr()
    assert "Warning: Unexpected error parsing skill" in captured.out


def test_indexer_preserves_skill_order(temp_dir: Path):
    """Test that indexer preserves the order of input skill paths."""
    skills = []
    for i in range(5):
        skill_dir = temp_dir / f"skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: skill-{i}
description: Skill number {i}
---
""")
        skills.append(skill_dir)
    
    indexer = SkillIndexer()
    descriptors = indexer.index_skills(skills)
    
    assert len(descriptors) == 5
    for i, descriptor in enumerate(descriptors):
        assert descriptor.name == f"skill-{i}"
        assert descriptor.path == skills[i]
