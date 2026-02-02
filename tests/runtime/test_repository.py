"""Tests for SkillsRepository."""

import tempfile
from pathlib import Path

import pytest

from agent_skills.exceptions import SkillNotFoundError
from agent_skills.models import ExecutionPolicy, ResourcePolicy, SkillDescriptor
from agent_skills.runtime.repository import SkillsRepository


@pytest.fixture
def temp_skill_dir():
    """Create a temporary directory with a test skill."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        
        # Create SKILL.md with valid frontmatter
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
license: MIT
---

# Test Skill Instructions

This is a test skill.
""")
        
        yield Path(tmpdir)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_repository_initialization():
    """Test that repository can be initialized with basic configuration."""
    repo = SkillsRepository(
        roots=[Path("./skills")],
        cache_dir=None,
        resource_policy=ResourcePolicy(),
        execution_policy=ExecutionPolicy(),
    )
    
    assert repo is not None
    assert repo._roots == [Path("./skills")]
    assert repo._cache is None


def test_repository_initialization_with_cache(temp_cache_dir):
    """Test that repository can be initialized with cache directory."""
    repo = SkillsRepository(
        roots=[Path("./skills")],
        cache_dir=temp_cache_dir,
    )
    
    assert repo is not None
    assert repo._cache is not None
    assert repo._cache.cache_dir == temp_cache_dir


def test_refresh_discovers_skills(temp_skill_dir):
    """Test that refresh() discovers skills in root directories."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    
    # Refresh should discover the test skill
    skills = repo.refresh()
    
    assert len(skills) == 1
    assert skills[0].name == "test-skill"
    assert skills[0].description == "A test skill for unit testing"
    assert skills[0].license == "MIT"


def test_refresh_with_cache(temp_skill_dir, temp_cache_dir):
    """Test that refresh() uses cache when available."""
    repo = SkillsRepository(
        roots=[temp_skill_dir],
        cache_dir=temp_cache_dir,
    )
    
    # First refresh - should parse and cache
    skills1 = repo.refresh()
    assert len(skills1) == 1
    
    # Second refresh - should use cache
    skills2 = repo.refresh()
    assert len(skills2) == 1
    assert skills2[0].name == skills1[0].name


def test_list_returns_discovered_skills(temp_skill_dir):
    """Test that list() returns all discovered skills."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    
    # Before refresh, list should be empty
    assert repo.list() == []
    
    # After refresh, list should contain discovered skills
    repo.refresh()
    skills = repo.list()
    
    assert len(skills) == 1
    assert skills[0].name == "test-skill"


def test_open_returns_skill_handle(temp_skill_dir):
    """Test that open() returns a SkillHandle for a discovered skill."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Open the skill
    handle = repo.open("test-skill")
    
    assert handle is not None
    assert handle.descriptor().name == "test-skill"


def test_open_raises_error_for_unknown_skill(temp_skill_dir):
    """Test that open() raises SkillNotFoundError for unknown skills."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Try to open a non-existent skill
    with pytest.raises(SkillNotFoundError) as exc_info:
        repo.open("non-existent-skill")
    
    assert "non-existent-skill" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


def test_open_before_refresh_raises_error():
    """Test that open() raises error if called before refresh()."""
    repo = SkillsRepository(roots=[Path("./skills")])
    
    # Try to open a skill before refresh
    with pytest.raises(SkillNotFoundError):
        repo.open("any-skill")


def test_refresh_with_multiple_roots(temp_skill_dir):
    """Test that refresh() discovers skills from multiple root directories."""
    # Create a second skill directory
    skill_dir2 = temp_skill_dir / "skill2"
    skill_dir2.mkdir()
    
    skill_md2 = skill_dir2 / "SKILL.md"
    skill_md2.write_text("""---
name: test-skill-2
description: Second test skill
---

# Second Skill
""")
    
    # Create repository with both directories as roots
    repo = SkillsRepository(roots=[temp_skill_dir / "test-skill", skill_dir2])
    skills = repo.refresh()
    
    # Should discover both skills
    assert len(skills) == 2
    skill_names = {s.name for s in skills}
    assert "test-skill" in skill_names
    assert "test-skill-2" in skill_names


def test_refresh_handles_invalid_skills_gracefully(temp_skill_dir):
    """Test that refresh() continues when encountering invalid skills."""
    # Create an invalid skill (missing required field)
    invalid_skill_dir = temp_skill_dir / "invalid-skill"
    invalid_skill_dir.mkdir()
    
    invalid_skill_md = invalid_skill_dir / "SKILL.md"
    invalid_skill_md.write_text("""---
name: invalid-skill
# Missing description field
---

# Invalid Skill
""")
    
    # Repository should still discover the valid skill
    repo = SkillsRepository(roots=[temp_skill_dir])
    skills = repo.refresh()
    
    # Should only have the valid skill
    assert len(skills) == 1
    assert skills[0].name == "test-skill"


def test_repository_with_policies(temp_skill_dir):
    """Test that repository passes policies to SkillHandle."""
    resource_policy = ResourcePolicy(max_file_bytes=50_000)
    execution_policy = ExecutionPolicy(enabled=True, allow_skills={"test-skill"})
    
    repo = SkillsRepository(
        roots=[temp_skill_dir],
        resource_policy=resource_policy,
        execution_policy=execution_policy,
    )
    repo.refresh()
    
    # Open skill and verify policies are passed
    handle = repo.open("test-skill")
    
    assert handle._resource_policy.max_file_bytes == 50_000
    assert handle._execution_policy.enabled is True
    assert "test-skill" in handle._execution_policy.allow_skills


def test_to_prompt_claude_xml_format(temp_skill_dir):
    """Test to_prompt() with Claude XML format."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Render with Claude XML format
    result = repo.to_prompt(format="claude_xml", include_location=True)
    
    # Verify XML structure
    assert "<available_skills>" in result
    assert "</available_skills>" in result
    assert "<skill" in result
    assert 'name="test-skill"' in result
    assert 'description="A test skill for unit testing"' in result
    assert "location=" in result


def test_to_prompt_claude_xml_without_location(temp_skill_dir):
    """Test to_prompt() with Claude XML format without location."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Render without location
    result = repo.to_prompt(format="claude_xml", include_location=False)
    
    # Verify XML structure
    assert "<available_skills>" in result
    assert "</available_skills>" in result
    assert "<skill" in result
    assert 'name="test-skill"' in result
    assert 'description="A test skill for unit testing"' in result
    assert "location=" not in result


def test_to_prompt_json_format(temp_skill_dir):
    """Test to_prompt() with JSON format."""
    import json
    
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Render with JSON format
    result = repo.to_prompt(format="json", include_location=True)
    
    # Verify it's valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "test-skill"
    assert parsed[0]["description"] == "A test skill for unit testing"
    assert "location" in parsed[0]


def test_to_prompt_json_without_location(temp_skill_dir):
    """Test to_prompt() with JSON format without location."""
    import json
    
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Render without location
    result = repo.to_prompt(format="json", include_location=False)
    
    # Verify it's valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "test-skill"
    assert parsed[0]["description"] == "A test skill for unit testing"
    assert "location" not in parsed[0]


def test_to_prompt_invalid_format(temp_skill_dir):
    """Test to_prompt() raises error for invalid format."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Try invalid format
    with pytest.raises(ValueError) as exc_info:
        repo.to_prompt(format="invalid_format")
    
    assert "Invalid format" in str(exc_info.value)
    assert "invalid_format" in str(exc_info.value)
    assert "claude_xml" in str(exc_info.value)
    assert "json" in str(exc_info.value)


def test_to_prompt_empty_repository():
    """Test to_prompt() with no skills discovered."""
    import json
    
    # Create repository with non-existent directory
    repo = SkillsRepository(roots=[Path("/nonexistent")])
    repo.refresh()
    
    # Claude XML format should return empty structure
    xml_result = repo.to_prompt(format="claude_xml")
    assert "<available_skills>" in xml_result
    assert "</available_skills>" in xml_result
    
    # JSON format should return empty array
    json_result = repo.to_prompt(format="json")
    parsed = json.loads(json_result)
    assert parsed == []


def test_to_prompt_multiple_skills(temp_skill_dir):
    """Test to_prompt() with multiple skills."""
    import json
    
    # Create a second skill
    skill_dir2 = temp_skill_dir / "skill2"
    skill_dir2.mkdir()
    
    skill_md2 = skill_dir2 / "SKILL.md"
    skill_md2.write_text("""---
name: test-skill-2
description: Second test skill
---

# Second Skill
""")
    
    # Create repository with both skills
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Test Claude XML format
    xml_result = repo.to_prompt(format="claude_xml", include_location=False)
    assert 'name="test-skill"' in xml_result
    assert 'name="test-skill-2"' in xml_result
    assert xml_result.count("<skill") == 2
    
    # Test JSON format
    json_result = repo.to_prompt(format="json", include_location=False)
    parsed = json.loads(json_result)
    assert len(parsed) == 2
    skill_names = {s["name"] for s in parsed}
    assert "test-skill" in skill_names
    assert "test-skill-2" in skill_names


def test_to_prompt_before_refresh():
    """Test to_prompt() before calling refresh()."""
    import json
    
    repo = SkillsRepository(roots=[Path("./skills")])
    
    # Should return empty results before refresh
    xml_result = repo.to_prompt(format="claude_xml")
    assert "<available_skills>" in xml_result
    assert "</available_skills>" in xml_result
    
    json_result = repo.to_prompt(format="json")
    parsed = json.loads(json_result)
    assert parsed == []


def test_to_prompt_default_parameters(temp_skill_dir):
    """Test to_prompt() with default parameters."""
    repo = SkillsRepository(roots=[temp_skill_dir])
    repo.refresh()
    
    # Call with defaults (should be claude_xml with location)
    result = repo.to_prompt()
    
    # Should be Claude XML format
    assert "<available_skills>" in result
    assert "</available_skills>" in result
    assert 'name="test-skill"' in result
    # Should include location by default
    assert "location=" in result

