#!/usr/bin/env python3
"""
Snaptube Clone - Video Downloader
A modern video downloader similar to Snaptube, powered by yt-dlp.

Supported platforms:
- YouTube, Facebook, TikTok, Instagram, Twitter/X, Reddit, Vimeo, and more!
"""

import sys
import os

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    """Application entry point."""
    try:
        app = MainWindow()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Application closed by user.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()