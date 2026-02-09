"""Filesystem scanning for skill discovery."""

from pathlib import Path


class SkillScanner:
    """Scans filesystem for skills.

    A skill is identified by the presence of a SKILL.md file in a directory.
    The scanner recursively searches through provided root directories to find
    all directories containing SKILL.md files.
    """

    def scan(self, roots: list[Path]) -> list[Path]:
        """Find all directories containing SKILL.md.

        Args:
            roots: List of root directories to scan recursively

        Returns:
            List of Path objects pointing to directories containing SKILL.md files

        Example:
            >>> scanner = SkillScanner()
            >>> skills = scanner.scan([Path("./skills"), Path("~/.agent-skills")])
            >>> print(f"Found {len(skills)} skills")
        """
        skill_paths = []

        for root in roots:
            # Expand user home directory if present
            root = root.expanduser()

            # Skip if root doesn't exist or isn't a directory
            if not root.exists() or not root.is_dir():
                continue

            # Recursively find all SKILL.md files
            for skill_md in root.rglob("SKILL.md"):
                # The skill directory is the parent of SKILL.md
                skill_dir = skill_md.parent
                skill_paths.append(skill_dir)

        return skill_paths
