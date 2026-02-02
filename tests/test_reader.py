"""Unit tests for ResourceReader."""

import pytest
from pathlib import Path
from agent_skills.resources.reader import ResourceReader
from agent_skills.models import ResourcePolicy
from agent_skills.exceptions import ResourceTooLargeError


@pytest.fixture
def temp_text_file(tmp_path):
    """Create a temporary text file."""
    file_path = tmp_path / "test.txt"
    content = "Hello, World!\nThis is a test file.\n"
    file_path.write_text(content, encoding='utf-8')
    return file_path, content


@pytest.fixture
def temp_large_text_file(tmp_path):
    """Create a large temporary text file."""
    file_path = tmp_path / "large.txt"
    # Create a file larger than default max_file_bytes (200KB)
    content = "A" * 250_000  # 250KB
    file_path.write_text(content, encoding='utf-8')
    return file_path, content


@pytest.fixture
def temp_binary_file(tmp_path):
    """Create a temporary binary file."""
    file_path = tmp_path / "test.bin"
    content = bytes([0, 1, 2, 3, 4, 5, 255, 254, 253])
    file_path.write_bytes(content)
    return file_path, content


@pytest.fixture
def default_policy():
    """Create a default ResourcePolicy."""
    return ResourcePolicy()


@pytest.fixture
def strict_policy():
    """Create a strict ResourcePolicy with low limits."""
    return ResourcePolicy(
        max_file_bytes=100,
        max_total_bytes_per_session=500,
        binary_max_bytes=100
    )


class TestResourceReaderTextFiles:
    """Tests for reading text files."""
    
    def test_read_small_text_file(self, temp_text_file, default_policy):
        """Test reading a small text file."""
        file_path, expected_content = temp_text_file
        reader = ResourceReader(default_policy)
        
        content, truncated = reader.read_text(file_path)
        
        assert content == expected_content
        assert truncated is False
        assert reader.get_session_bytes_read() == len(expected_content.encode('utf-8'))
    
    def test_read_text_file_with_truncation(self, temp_large_text_file, default_policy):
        """Test reading a large text file that gets truncated."""
        file_path, full_content = temp_large_text_file
        reader = ResourceReader(default_policy)
        
        content, truncated = reader.read_text(file_path)
        
        assert len(content) <= default_policy.max_file_bytes
        assert truncated is True
        assert content == full_content[:len(content)]
    
    def test_read_text_file_with_custom_max_bytes(self, temp_text_file, default_policy):
        """Test reading a text file with custom max_bytes."""
        file_path, full_content = temp_text_file
        reader = ResourceReader(default_policy)
        
        # Read only first 5 bytes
        content, truncated = reader.read_text(file_path, max_bytes=5)
        
        assert len(content) <= 5
        assert truncated is True
    
    def test_read_text_file_tracks_session_bytes(self, temp_text_file, default_policy):
        """Test that reading multiple files tracks total session bytes."""
        file_path, content_str = temp_text_file
        reader = ResourceReader(default_policy)
        
        # Read the file twice
        content1, _ = reader.read_text(file_path)
        content2, _ = reader.read_text(file_path)
        
        expected_bytes = len(content_str.encode('utf-8')) * 2
        assert reader.get_session_bytes_read() == expected_bytes
    
    def test_read_text_file_exceeds_session_limit(self, temp_text_file, strict_policy):
        """Test that reading exceeds session byte limit."""
        file_path, _ = temp_text_file
        reader = ResourceReader(strict_policy)
        
        # Read multiple times to exceed session limit
        reader.read_text(file_path)  # First read should work
        reader.read_text(file_path)  # Second read should work
        
        # Eventually we should hit the limit
        with pytest.raises(ResourceTooLargeError) as exc_info:
            for _ in range(20):  # Keep reading until we hit the limit
                reader.read_text(file_path)
        
        assert "Session byte limit exceeded" in str(exc_info.value)
    
    def test_read_text_file_at_session_limit(self, strict_policy, tmp_path):
        """Test reading when already at session limit."""
        # Create a small file
        file_path = tmp_path / "small.txt"
        file_path.write_text("X" * 100, encoding='utf-8')
        
        reader = ResourceReader(strict_policy)
        
        # Read until we're at the limit
        for _ in range(5):  # 5 * 100 = 500 bytes (at limit)
            reader.read_text(file_path)
        
        # Next read should fail
        with pytest.raises(ResourceTooLargeError):
            reader.read_text(file_path)
    
    def test_reset_session_bytes(self, temp_text_file, default_policy):
        """Test resetting session byte counter."""
        file_path, _ = temp_text_file
        reader = ResourceReader(default_policy)
        
        # Read a file
        reader.read_text(file_path)
        assert reader.get_session_bytes_read() > 0
        
        # Reset counter
        reader.reset_session_bytes()
        assert reader.get_session_bytes_read() == 0


class TestResourceReaderBinaryFiles:
    """Tests for reading binary files."""
    
    def test_read_small_binary_file(self, temp_binary_file, default_policy):
        """Test reading a small binary file."""
        file_path, expected_content = temp_binary_file
        reader = ResourceReader(default_policy)
        
        content, truncated = reader.read_binary(file_path)
        
        assert content == expected_content
        assert truncated is False
        assert reader.get_session_bytes_read() == len(expected_content)
    
    def test_read_binary_file_with_truncation(self, default_policy, tmp_path):
        """Test reading a large binary file that gets truncated."""
        # Create a large binary file
        file_path = tmp_path / "large.bin"
        large_content = bytes(range(256)) * 10000  # ~2.5MB
        file_path.write_bytes(large_content)
        
        reader = ResourceReader(default_policy)
        
        content, truncated = reader.read_binary(file_path)
        
        assert len(content) <= default_policy.binary_max_bytes
        assert truncated is True
        assert content == large_content[:len(content)]
    
    def test_read_binary_file_with_custom_max_bytes(self, temp_binary_file, default_policy):
        """Test reading a binary file with custom max_bytes."""
        file_path, full_content = temp_binary_file
        reader = ResourceReader(default_policy)
        
        # Read only first 3 bytes
        content, truncated = reader.read_binary(file_path, max_bytes=3)
        
        assert len(content) == 3
        assert truncated is True
        assert content == full_content[:3]
    
    def test_read_binary_file_tracks_session_bytes(self, temp_binary_file, default_policy):
        """Test that reading multiple binary files tracks total session bytes."""
        file_path, binary_content = temp_binary_file
        reader = ResourceReader(default_policy)
        
        # Read the file twice
        content1, _ = reader.read_binary(file_path)
        content2, _ = reader.read_binary(file_path)
        
        expected_bytes = len(binary_content) * 2
        assert reader.get_session_bytes_read() == expected_bytes
    
    def test_read_binary_file_exceeds_session_limit(self, temp_binary_file, strict_policy):
        """Test that reading binary files exceeds session byte limit."""
        file_path, _ = temp_binary_file
        reader = ResourceReader(strict_policy)
        
        # Read multiple times to exceed session limit
        with pytest.raises(ResourceTooLargeError):
            for _ in range(100):  # Keep reading until we hit the limit
                reader.read_binary(file_path)


class TestResourceReaderMixedReads:
    """Tests for mixed text and binary reads."""
    
    def test_mixed_text_and_binary_reads(self, temp_text_file, temp_binary_file, default_policy):
        """Test that text and binary reads share the same session byte counter."""
        text_path, text_content = temp_text_file
        binary_path, binary_content = temp_binary_file
        reader = ResourceReader(default_policy)
        
        # Read text file
        reader.read_text(text_path)
        bytes_after_text = reader.get_session_bytes_read()
        
        # Read binary file
        reader.read_binary(binary_path)
        bytes_after_binary = reader.get_session_bytes_read()
        
        # Total should be sum of both
        expected_total = len(text_content.encode('utf-8')) + len(binary_content)
        assert bytes_after_binary == expected_total
        assert bytes_after_binary > bytes_after_text


class TestResourceReaderSHA256:
    """Tests for SHA256 hash computation."""
    
    def test_compute_sha256_string(self, default_policy):
        """Test computing SHA256 hash of a string."""
        reader = ResourceReader(default_policy)
        content = "Hello, World!"
        
        hash_value = reader.compute_sha256(content)
        
        # Known SHA256 hash of "Hello, World!"
        expected_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert hash_value == expected_hash
    
    def test_compute_sha256_bytes(self, default_policy):
        """Test computing SHA256 hash of bytes."""
        reader = ResourceReader(default_policy)
        content = b"Hello, World!"
        
        hash_value = reader.compute_sha256(content)
        
        # Known SHA256 hash of "Hello, World!"
        expected_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert hash_value == expected_hash
    
    def test_compute_sha256_empty(self, default_policy):
        """Test computing SHA256 hash of empty content."""
        reader = ResourceReader(default_policy)
        
        hash_value = reader.compute_sha256("")
        
        # Known SHA256 hash of empty string
        expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert hash_value == expected_hash


class TestResourceReaderEdgeCases:
    """Tests for edge cases."""
    
    def test_read_empty_text_file(self, tmp_path, default_policy):
        """Test reading an empty text file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("", encoding='utf-8')
        
        reader = ResourceReader(default_policy)
        content, truncated = reader.read_text(file_path)
        
        assert content == ""
        assert truncated is False
        assert reader.get_session_bytes_read() == 0
    
    def test_read_empty_binary_file(self, tmp_path, default_policy):
        """Test reading an empty binary file."""
        file_path = tmp_path / "empty.bin"
        file_path.write_bytes(b"")
        
        reader = ResourceReader(default_policy)
        content, truncated = reader.read_binary(file_path)
        
        assert content == b""
        assert truncated is False
        assert reader.get_session_bytes_read() == 0
    
    def test_read_text_file_with_unicode(self, tmp_path, default_policy):
        """Test reading a text file with Unicode characters."""
        file_path = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 Привет"
        file_path.write_text(content, encoding='utf-8')
        
        reader = ResourceReader(default_policy)
        read_content, truncated = reader.read_text(file_path)
        
        assert read_content == content
        assert truncated is False
    
    def test_read_nonexistent_file(self, tmp_path, default_policy):
        """Test reading a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.txt"
        reader = ResourceReader(default_policy)
        
        with pytest.raises(FileNotFoundError):
            reader.read_text(file_path)
    
    def test_session_limit_with_truncation(self, strict_policy, tmp_path):
        """Test that truncation respects session limits."""
        # Create a file larger than both file limit and session limit
        file_path = tmp_path / "large.txt"
        file_path.write_text("X" * 1000, encoding='utf-8')
        
        reader = ResourceReader(strict_policy)
        
        # First read should be truncated to file limit (100 bytes)
        content1, truncated1 = reader.read_text(file_path)
        assert len(content1) <= 100
        assert truncated1 is True
        
        # Continue reading until session limit
        # Session limit is 500, we've read ~100, so we can read ~400 more
        for _ in range(4):
            content, _ = reader.read_text(file_path)
        
        # Next read should fail due to session limit
        with pytest.raises(ResourceTooLargeError):
            reader.read_text(file_path)



class TestFullTextSearcher:
    """Tests for FullTextSearcher."""
    
    @pytest.fixture
    def search_directory(self, tmp_path):
        """Create a directory structure with test files for searching."""
        # Create directory structure
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()
        
        # Create some text files with searchable content
        (refs_dir / "api-docs.md").write_text(
            "# API Documentation\n"
            "This API provides authentication endpoints.\n"
            "Use the /auth/login endpoint to authenticate.\n",
            encoding='utf-8'
        )
        
        (refs_dir / "guide.txt").write_text(
            "Getting Started Guide\n"
            "First, configure your authentication credentials.\n"
            "Then, call the API endpoints.\n",
            encoding='utf-8'
        )
        
        # Create a subdirectory with more files
        sub_dir = refs_dir / "examples"
        sub_dir.mkdir()
        
        (sub_dir / "example1.md").write_text(
            "# Example 1\n"
            "This example shows authentication flow.\n"
            "Authentication is required for all endpoints.\n",
            encoding='utf-8'
        )
        
        (sub_dir / "example2.txt").write_text(
            "Example 2: Data Processing\n"
            "This example does not require authentication.\n"
            "Process data using the /data endpoint.\n",
            encoding='utf-8'
        )
        
        # Create a binary file (should be skipped)
        (refs_dir / "data.bin").write_bytes(b"\x00\x01\x02\x03\x04")
        
        return refs_dir
    
    def test_search_finds_matches(self, search_directory):
        """Test that search finds all matching lines."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "authentication")
        
        # Should find 5 matches across multiple files
        # (api-docs.md line 2, guide.txt line 2, example1.md lines 2 and 3, example2.txt line 2)
        assert len(results) == 5
        
        # Check that results have required fields
        for result in results:
            assert 'path' in result
            assert 'line_num' in result
            assert 'context' in result
            assert 'authentication' in result['context'].lower()
    
    def test_search_case_insensitive(self, search_directory):
        """Test that search is case-insensitive."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        
        # Search with different cases
        results_lower = searcher.search(search_directory, "authentication")
        results_upper = searcher.search(search_directory, "AUTHENTICATION")
        results_mixed = searcher.search(search_directory, "AuThEnTiCaTiOn")
        
        # All should return the same number of results
        assert len(results_lower) == len(results_upper) == len(results_mixed)
    
    def test_search_returns_correct_line_numbers(self, search_directory):
        """Test that search returns correct line numbers."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "API Documentation")
        
        # Should find one match on line 1
        assert len(results) == 1
        assert results[0]['line_num'] == 1
        assert "API Documentation" in results[0]['context']
    
    def test_search_returns_relative_paths(self, search_directory):
        """Test that search returns relative paths."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "Example 1")
        
        # Should find match in subdirectory
        assert len(results) == 1
        assert results[0]['path'] == str(Path("examples") / "example1.md")
    
    def test_search_respects_max_results(self, search_directory):
        """Test that search respects max_results limit."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        
        # Search for common word with limit
        results = searcher.search(search_directory, "the", max_results=3)
        
        # Should return at most 3 results
        assert len(results) <= 3
    
    def test_search_empty_query(self, search_directory):
        """Test searching with empty query."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "")
        
        # Empty query should match every line, but limited by max_results
        assert len(results) <= 20  # Default max_results
    
    def test_search_no_matches(self, search_directory):
        """Test searching for query with no matches."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "nonexistent_query_string_xyz")
        
        # Should return empty list
        assert len(results) == 0
    
    def test_search_nonexistent_directory(self, tmp_path):
        """Test searching in a directory that doesn't exist."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        nonexistent = tmp_path / "nonexistent"
        results = searcher.search(nonexistent, "test")
        
        # Should return empty list, not raise exception
        assert len(results) == 0
    
    def test_search_empty_directory(self, tmp_path):
        """Test searching in an empty directory."""
        from agent_skills.resources.reader import FullTextSearcher
        
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        searcher = FullTextSearcher()
        results = searcher.search(empty_dir, "test")
        
        # Should return empty list
        assert len(results) == 0
    
    def test_search_skips_binary_files(self, search_directory):
        """Test that search handles binary files gracefully."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        
        # Search for a term that only appears in text files
        results = searcher.search(search_directory, "API")
        
        # Should find matches only in text files, not binary
        # Check that all results are from text files
        for result in results:
            # Binary file might be read with errors='replace', but shouldn't match "API"
            assert "API" in result['context']
    
    def test_search_with_unicode(self, tmp_path):
        """Test searching with Unicode characters."""
        from agent_skills.resources.reader import FullTextSearcher
        
        # Create file with Unicode content
        unicode_dir = tmp_path / "unicode"
        unicode_dir.mkdir()
        (unicode_dir / "unicode.txt").write_text(
            "Hello 世界\n"
            "Привет мир\n"
            "🌍 Earth\n",
            encoding='utf-8'
        )
        
        searcher = FullTextSearcher()
        
        # Search for Unicode text
        results = searcher.search(unicode_dir, "世界")
        assert len(results) == 1
        assert "世界" in results[0]['context']
        
        results = searcher.search(unicode_dir, "Привет")
        assert len(results) == 1
        assert "Привет" in results[0]['context']
        
        results = searcher.search(unicode_dir, "🌍")
        assert len(results) == 1
        assert "🌍" in results[0]['context']
    
    def test_search_context_includes_full_line(self, search_directory):
        """Test that context includes the full matching line."""
        from agent_skills.resources.reader import FullTextSearcher
        
        searcher = FullTextSearcher()
        results = searcher.search(search_directory, "authentication endpoints")
        
        # Should find the line in api-docs.md
        assert len(results) == 1
        assert results[0]['context'] == "This API provides authentication endpoints."
    
    def test_search_multiple_matches_same_file(self, tmp_path):
        """Test that search finds multiple matches in the same file."""
        from agent_skills.resources.reader import FullTextSearcher
        
        # Create file with multiple matching lines
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "multi.txt").write_text(
            "First match here\n"
            "No match\n"
            "Second match here\n"
            "Third match here\n",
            encoding='utf-8'
        )
        
        searcher = FullTextSearcher()
        results = searcher.search(test_dir, "match here")
        
        # Should find 3 matches
        assert len(results) == 3
        assert results[0]['line_num'] == 1
        assert results[1]['line_num'] == 3
        assert results[2]['line_num'] == 4
    
    def test_search_strips_newlines_from_context(self, tmp_path):
        """Test that context has newlines stripped."""
        from agent_skills.resources.reader import FullTextSearcher
        
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "test.txt").write_text("test line\n", encoding='utf-8')
        
        searcher = FullTextSearcher()
        results = searcher.search(test_dir, "test")
        
        # Context should not have trailing newline
        assert len(results) == 1
        assert results[0]['context'] == "test line"
        assert not results[0]['context'].endswith('\n')
