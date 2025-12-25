"""Standalone entry point for playing Level 2 directly."""

from gametest import SpiralGame


def main() -> None:
    """Launch the game starting on Level 2."""
    SpiralGame(start_level=2).run()


if __name__ == "__main__":
    main()
