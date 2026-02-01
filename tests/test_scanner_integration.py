"""Integration tests for SkillScanner to verify requirements."""

from pathlib import Path

import pytest

from agent_skills.discovery import SkillScanner


def test_requirement_2_1_recursive_scan(temp_dir: Path):
    """Verify Requirement 2.1: Recursively scan for folders containing SKILL.md.
    
    WHEN provided with root directories, THE Agent_Skills_Runtime SHALL 
    recursively scan for folders containing SKILL.md
    """
    # Create a nested structure
    root = temp_dir / "skills"
    root.mkdir()
    
    # Top-level skill
    skill1 = root / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: skill-1\ndescription: Test\n---\n")
    
    # Nested skill
    category = root / "category"
    category.mkdir()
    skill2 = category / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: skill-2\ndescription: Test\n---\n")
    
    # Deeply nested skill
    subcategory = category / "subcategory"
    subcategory.mkdir()
    skill3 = subcategory / "skill-3"
    skill3.mkdir()
    (skill3 / "SKILL.md").write_text("---\nname: skill-3\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([root])
    
    # Should find all three skills regardless of nesting depth
    assert len(skills) == 3
    assert skill1 in skills
    assert skill2 in skills
    assert skill3 in skills


def test_requirement_2_4_multiple_root_directories(temp_dir: Path):
    """Verify Requirement 2.4: Support multiple skill root directories.
    
    THE Agent_Skills_Runtime SHALL support multiple skill root directories
    """
    # Create multiple root directories
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
    
    root3 = temp_dir / "root3"
    root3.mkdir()
    skill3 = root3 / "skill-3"
    skill3.mkdir()
    (skill3 / "SKILL.md").write_text("---\nname: skill-3\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([root1, root2, root3])
    
    # Should find skills from all root directories
    assert len(skills) == 3
    assert skill1 in skills
    assert skill2 in skills
    assert skill3 in skills


def test_scanner_returns_list_of_skill_paths(temp_dir: Path):
    """Verify that scanner returns a list of skill paths as specified.
    
    The scanner should return a list of Path objects pointing to directories
    containing SKILL.md files.
    """
    # Create skills
    skill1 = temp_dir / "skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: skill-1\ndescription: Test\n---\n")
    
    skill2 = temp_dir / "skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: skill-2\ndescription: Test\n---\n")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    # Verify return type
    assert isinstance(skills, list)
    assert len(skills) == 2
    
    # Verify all elements are Path objects
    for skill_path in skills:
        assert isinstance(skill_path, Path)
        assert skill_path.is_dir()
        assert (skill_path / "SKILL.md").exists()


def test_scanner_handles_mixed_valid_and_invalid_roots(temp_dir: Path):
    """Verify scanner handles a mix of valid and invalid root directories gracefully."""
    # Create one valid root
    valid_root = temp_dir / "valid"
    valid_root.mkdir()
    skill = valid_root / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: skill\ndescription: Test\n---\n")
    
    # Create invalid roots
    nonexistent_root = temp_dir / "nonexistent"
    file_root = temp_dir / "file.txt"
    file_root.write_text("not a directory")
    
    scanner = SkillScanner()
    skills = scanner.scan([valid_root, nonexistent_root, file_root])
    
    # Should only find the skill from the valid root
    assert len(skills) == 1
    assert skills[0] == skill


def test_scanner_with_complex_skill_structure(temp_dir: Path):
    """Verify scanner works with skills that have complex directory structures."""
    # Create a skill with all subdirectories
    skill = temp_dir / "complex-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: complex-skill\ndescription: Test\n---\n")
    
    # Add references
    refs = skill / "references"
    refs.mkdir()
    (refs / "doc1.md").write_text("Documentation 1")
    (refs / "doc2.md").write_text("Documentation 2")
    nested_refs = refs / "nested"
    nested_refs.mkdir()
    (nested_refs / "doc3.md").write_text("Documentation 3")
    
    # Add assets
    assets = skill / "assets"
    assets.mkdir()
    (assets / "data.txt").write_text("Data")
    (assets / "image.png").write_bytes(b"fake image data")
    
    # Add scripts
    scripts = skill / "scripts"
    scripts.mkdir()
    (scripts / "setup.sh").write_text("#!/bin/bash\necho 'setup'")
    (scripts / "process.py").write_text("#!/usr/bin/env python3\nprint('process')")
    
    scanner = SkillScanner()
    skills = scanner.scan([temp_dir])
    
    # Should find the skill despite complex structure
    assert len(skills) == 1
    assert skills[0] == skill
    
    # Verify the skill structure is intact
    assert (skills[0] / "SKILL.md").exists()
    assert (skills[0] / "references").is_dir()
    assert (skills[0] / "assets").is_dir()
    assert (skills[0] / "scripts").is_dir()
