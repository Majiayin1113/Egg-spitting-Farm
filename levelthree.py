"""Standalone entry point for playing Level 3 directly."""

from gametest import SpiralGame


def main() -> None:
    """Launch the game starting on Level 3."""
    SpiralGame(start_level=3).run()


if __name__ == "__main__":
    main()
