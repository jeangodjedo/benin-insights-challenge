"""
Pytest configuration file.

Adds the project root to sys.path so that 'pipeline' is importable
as a package from any test file without manual sys.path manipulation.

Placed at the project root, this file is automatically loaded by pytest
before any test collection begins.
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))