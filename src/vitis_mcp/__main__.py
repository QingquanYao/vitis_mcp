"""Entry point: python -m vitis_mcp"""

from vitis_mcp.server import mcp


def main():
    mcp.run()


if __name__ == "__main__":
    main()
