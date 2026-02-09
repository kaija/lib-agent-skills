"""File reading with policy enforcement and size limits."""

import hashlib
from pathlib import Path
from typing import TypedDict
from agent_skills.models import ResourcePolicy
from agent_skills.exceptions import ResourceTooLargeError


class SearchResult(TypedDict):
    """Type definition for search results."""
    path: str
    line_num: int
    context: str


class ResourceReader:
    """Reads files with policy enforcement.

    This class handles reading both text and binary files while enforcing
    size limits and tracking total bytes read per session.
    """

    def __init__(self, policy: ResourcePolicy):
        """Initialize with resource policy.

        Args:
            policy: ResourcePolicy defining size limits and allowed extensions
        """
        self.policy = policy
        self.session_bytes_read = 0

    def read_text(
        self,
        path: Path,
        max_bytes: int | None = None
    ) -> tuple[str, bool]:
        """Read text file with size limits.

        Args:
            path: Path to the file to read
            max_bytes: Optional override for max file size (defaults to policy.max_file_bytes)

        Returns:
            Tuple of (content, truncated) where:
            - content: The file content as a string
            - truncated: True if content was truncated due to size limits

        Raises:
            ResourceTooLargeError: If total session bytes exceed max_total_bytes_per_session
        """
        # Use policy default if max_bytes not specified
        if max_bytes is None:
            max_bytes = self.policy.max_file_bytes

        # Check if we can read any more bytes in this session
        if self.session_bytes_read >= self.policy.max_total_bytes_per_session:
            raise ResourceTooLargeError(
                f"Session byte limit exceeded: {self.session_bytes_read} >= "
                f"{self.policy.max_total_bytes_per_session}"
            )

        # Calculate how many bytes we can still read in this session
        remaining_session_bytes = (
            self.policy.max_total_bytes_per_session - self.session_bytes_read
        )

        # Limit read to the smaller of max_bytes and remaining session bytes
        effective_max_bytes = min(max_bytes, remaining_session_bytes)

        # Read the file with size limit
        truncated = False
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                # Read up to effective_max_bytes
                content = f.read(effective_max_bytes)

                # Check if there's more content (file was truncated)
                if f.read(1):  # Try to read one more byte
                    truncated = True
        except UnicodeDecodeError:
            # If we can't decode as UTF-8, try with error replacement
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(effective_max_bytes)
                if f.read(1):
                    truncated = True

        # Update session byte counter
        bytes_read = len(content.encode('utf-8'))
        self.session_bytes_read += bytes_read

        # Check if we've now exceeded the session limit
        if self.session_bytes_read > self.policy.max_total_bytes_per_session:
            raise ResourceTooLargeError(
                f"Session byte limit exceeded after read: {self.session_bytes_read} > "
                f"{self.policy.max_total_bytes_per_session}"
            )

        return content, truncated

    def read_binary(
        self,
        path: Path,
        max_bytes: int | None = None
    ) -> tuple[bytes, bool]:
        """Read binary file with size limits.

        Args:
            path: Path to the file to read
            max_bytes: Optional override for max file size (defaults to policy.binary_max_bytes)

        Returns:
            Tuple of (content, truncated) where:
            - content: The file content as bytes
            - truncated: True if content was truncated due to size limits

        Raises:
            ResourceTooLargeError: If total session bytes exceed max_total_bytes_per_session
        """
        # Use policy default if max_bytes not specified
        if max_bytes is None:
            max_bytes = self.policy.binary_max_bytes

        # Check if we can read any more bytes in this session
        if self.session_bytes_read >= self.policy.max_total_bytes_per_session:
            raise ResourceTooLargeError(
                f"Session byte limit exceeded: {self.session_bytes_read} >= "
                f"{self.policy.max_total_bytes_per_session}"
            )

        # Calculate how many bytes we can still read in this session
        remaining_session_bytes = (
            self.policy.max_total_bytes_per_session - self.session_bytes_read
        )

        # Limit read to the smaller of max_bytes and remaining session bytes
        effective_max_bytes = min(max_bytes, remaining_session_bytes)

        # Read the file with size limit
        truncated = False
        with open(path, 'rb') as f:
            content = f.read(effective_max_bytes)

            # Check if there's more content (file was truncated)
            if f.read(1):  # Try to read one more byte
                truncated = True

        # Update session byte counter
        bytes_read = len(content)
        self.session_bytes_read += bytes_read

        # Check if we've now exceeded the session limit
        if self.session_bytes_read > self.policy.max_total_bytes_per_session:
            raise ResourceTooLargeError(
                f"Session byte limit exceeded after read: {self.session_bytes_read} > "
                f"{self.policy.max_total_bytes_per_session}"
            )

        return content, truncated

    def compute_sha256(self, content: str | bytes) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: String or bytes to hash

        Returns:
            Hexadecimal SHA256 hash string
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def reset_session_bytes(self) -> None:
        """Reset the session byte counter.

        This should be called when starting a new session.
        """
        self.session_bytes_read = 0

    def get_session_bytes_read(self) -> int:
        """Get the total bytes read in this session.

        Returns:
            Total bytes read so far in this session
        """
        return self.session_bytes_read


class FullTextSearcher:
    """Searches text files for query strings.

    This class provides full-text search functionality across all text files
    in a directory, returning matches with context.
    """

    def search(
        self,
        directory: Path,
        query: str,
        max_results: int = 20
    ) -> list[SearchResult]:
        """Search all text files in directory for query string.

        Args:
            directory: Directory to search in (searches recursively)
            query: Search query string (case-insensitive substring match)
            max_results: Maximum number of results to return (default: 20)

        Returns:
            List of SearchResult dicts containing:
            - path: Relative path to the file from the search directory
            - line_num: Line number where match was found (1-indexed)
            - context: The matching line with surrounding context

        Note:
            - Search is case-insensitive
            - Only searches text files (attempts to decode as UTF-8)
            - Returns up to max_results matches to prevent excessive response size
            - Context includes the matching line only (not surrounding lines)
        """
        results: list[SearchResult] = []
        query_lower = query.lower()

        # If directory doesn't exist, return empty results
        if not directory.exists() or not directory.is_dir():
            return results

        # Recursively search all files in directory
        for file_path in directory.rglob('*'):
            # Skip directories
            if not file_path.is_file():
                continue

            # Skip if we've already found enough results
            if len(results) >= max_results:
                break

            # Try to read as text file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for line_num, line in enumerate(f, start=1):
                        # Check if query is in line (case-insensitive)
                        if query_lower in line.lower():
                            # Get relative path from search directory
                            try:
                                rel_path = file_path.relative_to(directory)
                            except ValueError:
                                # If relative_to fails, use absolute path
                                rel_path = file_path

                            # Add result with context (the matching line, stripped)
                            results.append({
                                'path': str(rel_path),
                                'line_num': line_num,
                                'context': line.rstrip('\n\r')
                            })

                            # Check if we've hit the limit
                            if len(results) >= max_results:
                                return results

            except (UnicodeDecodeError, PermissionError, OSError):
                # Skip files that can't be read as text or have permission issues
                continue

        return results
