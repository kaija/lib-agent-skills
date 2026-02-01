"""Unit tests for SkillScanner."""

from pathlib import Path

import pytest

from agent_skills.discovery import SkillScanner


def test_scanner_finds_single_skill(temp_dir: Path):
    """Test that scanner finds a single skill directory."""
    # Create a skill directory with SKILL.md
    skill_dir = temp_dir / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: my-skill\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 1
    assert skills[0] == skill_dir


def test_scanner_finds_multiple_skills(temp_dir: Path):
    """Test that scanner finds multiple skills in the same root."""
    # Create multiple skill directories
    skill1 = temp_dir / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: skill-1\ndescription: Test\n---\n")
    
    skill2 = temp_dir / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: skill-2\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 2
    assert skill1 in skills
    assert skill2 in skills


def test_scanner_finds_nested_skills(temp_dir: Path):
    """Test that scanner finds skills in nested directories."""
    # Create nested skill directories
    nested_dir = temp_dir / "category" / "subcategory"
    nested_dir.mkdir(parents=True)
    (nested_dir / "SKILL.md").write_text("---\nname: nested-skill\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 1
    assert skills[0] == nested_dir


def test_scanner_supports_multiple_roots(temp_dir: Path):
    """Test that scanner supports multiple root directories."""
    # Create two separate root directories
    root1 = temp_dir / "root1"
    root1.mkdir()
    skill1 = root1 / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: skill-1\ndescription: Test\n---\n")
    
    root2 = temp_dir / "root2"
    root2.mkdir()
    skill2 = root2 / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: skill-2\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([root1, root2])
    
    assert len(skills) == 2
    assert skill1 in skills
    assert skill2 in skills


def test_scanner_ignores_non_skill_directories(temp_dir: Path):
    """Test that scanner ignores directories without SKILL.md."""
    # Create directories without SKILL.md
    (temp_dir / "not-a-skill").mkdir()
    (temp_dir / "also-not-a-skill").mkdir()
    
    # Create one valid skill
    skill_dir = temp_dir / "valid-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: valid-skill\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 1
    assert skills[0] == skill_dir


def test_scanner_handles_nonexistent_root(temp_dir: Path):
    """Test that scanner handles non-existent root directories gracefully."""
    nonexistent = temp_dir / "does-not-exist"
    
    scanner = SkillScanner()
    skills = scanner.scan([nonexistent])
    
    assert len(skills) == 0


def test_scanner_handles_file_as_root(temp_dir: Path):
    """Test that scanner handles a file path as root gracefully."""
    # Create a file instead of a directory
    file_path = temp_dir / "not-a-directory.txt"
    file_path.write_text("This is a file")
    
    scanner = SkillScanner()
    skills = scanner.scan([file_path])
    
    assert len(skills) == 0


def test_scanner_expands_user_home():
    """Test that scanner expands ~ in paths."""
    scanner = SkillScanner()
    
    # This should not raise an error even if the path doesn't exist
    # The scanner should expand ~ and then skip non-existent paths
    skills = scanner.scan([Path("~/nonexistent-skills-directory")])
    
    assert len(skills) == 0


def test_scanner_returns_skill_directory_not_skill_md(temp_dir: Path):
    """Test that scanner returns the skill directory, not the SKILL.md file path."""
    skill_dir = temp_dir / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: my-skill\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 1
    assert skills[0] == skill_dir
    assert skills[0] != skill_md


def test_scanner_with_empty_root_list():
    """Test that scanner handles empty root list."""
    scanner = SkillScanner()
    skills = scanner.scan([])
    
    assert len(skills) == 0


def test_scanner_finds_skills_with_subdirectories(temp_dir: Path):
    """Test that scanner finds skills that have subdirectories (references, assets, scripts)."""
    skill_dir = temp_dir / "full-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: full-skill\ndescription: Test\n---\n")
    
    # Create subdirectories
    (skill_dir / "references").mkdir()
    (skill_dir / "assets").mkdir()
    (skill_dir / "scripts").mkdir()
    
    # Add files to subdirectories
    (skill_dir / "references" / "doc.md").write_text("Documentation")
    (skill_dir / "assets" / "data.txt").write_text("Data")
    (skill_dir / "scripts" / "run.py").write_text("#!/usr/bin/env python3\nprint('hello')")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    assert len(skills) == 1
    assert skills[0] == skill_dir


def test_scanner_does_not_find_skill_md_in_subdirectories_as_separate_skills(temp_dir: Path):
    """Test that SKILL.md files in subdirectories are found as separate skills."""
    # Create a parent skill
    parent_skill = temp_dir / "parent-skill"
    parent_skill.mkdir()
    (parent_skill / "SKILL.md").write_text("---\nname: parent-skill\ndescription: Parent\n---\n")
    
    # Create a nested skill (this is a valid use case - skills can be nested)
    nested_skill = parent_skill / "nested-skill"
    nested_skill.mkdir()
    (nested_skill / "SKILL.md").write_text("---\nname: nested-skill\ndescription: Nested\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    # Both should be found as separate skills
    assert len(skills) == 2
    assert parent_skill in skills
    assert nested_skill in skills
