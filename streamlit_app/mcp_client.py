import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MCP_SERVER_DIR = PROJECT_ROOT / "mcp_server"
MCP_SERVER_FILE = MCP_SERVER_DIR / "server.py"


# ---------------------------------------------------------
# MCP server configuration
# ---------------------------------------------------------

def get_server_parameters():
    """
    Configuration used to start the local MCP server
    as a subprocess.
    """

    return StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_FILE)],
        env=os.environ.copy(),
    )


# ---------------------------------------------------------
# Call MCP tool
# ---------------------------------------------------------

async def _call_tool(tool_name: str, arguments: dict):
    """
    Start the MCP server, initialize the MCP session,
    call a tool, and return the result.
    """

    server_params = get_server_parameters()

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments=arguments,
            )

            return result


# ---------------------------------------------------------
# Read MCP resource
# ---------------------------------------------------------

async def _read_resource(resource_uri: str):
    """
    Start the MCP server and read an MCP resource.
    """

    server_params = get_server_parameters()

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.read_resource(resource_uri)

            return result


# ---------------------------------------------------------
# Synchronous wrappers
# ---------------------------------------------------------

def call_tool(tool_name: str, arguments: dict):
    """
    Synchronous wrapper that Streamlit can call.
    """

    return asyncio.run(
        _call_tool(tool_name, arguments)
    )


def read_resource(resource_uri: str):
    """
    Synchronous wrapper that Streamlit can call.
    """

    return asyncio.run(
        _read_resource(resource_uri)
    )


# ---------------------------------------------------------
# Connectivity test
# ---------------------------------------------------------

def main():

    print("========================================")
    print("MCP CLIENT CONNECTIVITY TEST")
    print("========================================")

    # -----------------------------------------
    # Test 1: ping
    # -----------------------------------------

    print("\n1. Testing MCP ping tool...")

    result = call_tool(
        "ping",
        {}
    )

    print("\nPing result:")
    print(result)

    # -----------------------------------------
    # Test 2: data dictionary
    # -----------------------------------------

    print("\n2. Reading MCP data dictionary...")

    dictionary = read_resource(
        "warehouse://data-dictionary"
    )

    print("\nData dictionary:")
    print(dictionary)

    print("\n========================================")
    print("MCP CLIENT TEST SUCCESSFUL")
    print("========================================")


if __name__ == "__main__":
    main()