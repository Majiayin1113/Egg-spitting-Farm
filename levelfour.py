"""Standalone entry point for playing Level 4 directly."""

from gametest import SpiralGame


def main() -> None:
    """Launch the game starting on Level 4."""
    SpiralGame(start_level=4).run()


if __name__ == "__main__":
    main()
