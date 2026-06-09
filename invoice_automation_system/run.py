#!/usr/bin/env python3
"""Simple entry point for the invoice automation system."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main_processor import main

if __name__ == "__main__":
    main()
