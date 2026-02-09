"""Frontmatter parsing for SKILL.md files."""

import hashlib
from pathlib import Path
from typing import Tuple

import yaml

from agent_skills.exceptions import SkillParseError


class FrontmatterParser:
    """Parses YAML frontmatter from SKILL.md files."""

    def parse(self, skill_path: Path) -> Tuple[dict, int]:
        """
        Parse frontmatter and return (metadata_dict, body_offset).

        Reads line-by-line until second '---' delimiter.

        Args:
            skill_path: Path to the skill directory containing SKILL.md

        Returns:
            Tuple of (metadata dict, byte offset where body starts)

        Raises:
            SkillParseError: If SKILL.md is missing, frontmatter is invalid,
                           or required fields are missing
        """
        skill_md_path = skill_path / "SKILL.md"

        if not skill_md_path.exists():
            raise SkillParseError(f"SKILL.md not found at {skill_md_path}")

        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                # Read first line - should be '---'
                first_line = f.readline()
                if not first_line.strip() == '---':
                    raise SkillParseError(
                        f"SKILL.md must start with '---' delimiter, got: {first_line.strip()}"
                    )

                # Collect frontmatter lines
                frontmatter_lines = []
                frontmatter_start = len(first_line)
                current_pos = frontmatter_start

                while True:
                    line = f.readline()
                    if not line:
                        raise SkillParseError(
                            "SKILL.md ended before finding second '---' delimiter"
                        )

                    current_pos += len(line)

                    if line.strip() == '---':
                        # Found second delimiter
                        body_offset = current_pos
                        break

                    frontmatter_lines.append(line)

                # Join and parse YAML
                frontmatter_text = ''.join(frontmatter_lines)

                try:
                    metadata = yaml.safe_load(frontmatter_text)
                except yaml.YAMLError as e:
                    raise SkillParseError(f"Invalid YAML in frontmatter: {e}")

                if metadata is None:
                    metadata = {}

                if not isinstance(metadata, dict):
                    raise SkillParseError(
                        f"Frontmatter must be a YAML dictionary, got {type(metadata).__name__}"
                    )

                # Validate required fields
                if 'name' not in metadata:
                    raise SkillParseError("Frontmatter missing required field: name")
                if 'description' not in metadata:
                    raise SkillParseError("Frontmatter missing required field: description")

                # Compute SHA256 hash of frontmatter content
                # Hash the raw frontmatter text (between the delimiters)
                frontmatter_hash = hashlib.sha256(
                    frontmatter_text.encode('utf-8')
                ).hexdigest()

                # Add hash to metadata
                metadata['_frontmatter_hash'] = frontmatter_hash

                return metadata, body_offset

        except SkillParseError:
            raise
        except Exception as e:
            raise SkillParseError(f"Error reading SKILL.md: {e}")
