#!/usr/bin/env python3
"""Simple test script that prints hello."""

import sys

def main():
    """Print hello message."""
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
