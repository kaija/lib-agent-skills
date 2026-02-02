#!/usr/bin/env python3
"""Setup script for data processor skill.

This script validates the environment and dependencies.
"""

import sys
import json


def check_python_version():
    """Check Python version is 3.10+."""
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher required", file=sys.stderr)
        return False
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """Check required dependencies are available."""
    required = ["json", "csv", "pathlib"]
    missing = []
    
    for module in required:
        try:
            __import__(module)
            print(f"✓ Module available: {module}")
        except ImportError:
            missing.append(module)
            print(f"✗ Module missing: {module}", file=sys.stderr)
    
    return len(missing) == 0


def validate_environment():
    """Validate environment configuration."""
    import os
    
    max_size = os.getenv("DATA_PROCESSOR_MAX_SIZE", "10")
    encoding = os.getenv("DATA_PROCESSOR_ENCODING", "utf-8")
    delimiter = os.getenv("DATA_PROCESSOR_DELIMITER", ",")
    
    print(f"✓ Max file size: {max_size}MB")
    print(f"✓ File encoding: {encoding}")
    print(f"✓ CSV delimiter: {delimiter}")
    
    return True


def main():
    """Run setup validation."""
    print("=" * 60)
    print("Data Processor Setup")
    print("=" * 60)
    print()
    
    print("Checking Python version...")
    if not check_python_version():
        return 1
    print()
    
    print("Checking dependencies...")
    if not check_dependencies():
        return 1
    print()
    
    print("Validating environment...")
    if not validate_environment():
        return 1
    print()
    
    print("=" * 60)
    print("Setup complete! Data processor is ready to use.")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
