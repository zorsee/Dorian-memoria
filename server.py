from pathlib import Path

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

server = Server("mcp-file-server")
sse = SseServerTransport("/messages/")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available file operation tools."""
    return [
        Tool(
            name="read_file",
            description="Read the contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="list_directory",
            description="List files and directories in a path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to list",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_directory",
            description="Create a new directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the directory to create",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delete_file",
            description="Delete a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to delete",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="file_info",
            description="Get information about a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to get info about",
                    }
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for file operations."""
    try:
        if name == "read_file":
            path = Path(arguments["path"])
            if not path.exists():
                return [TextContent(type="text", text=f"Error: File not found: {path}")]
            if not path.is_file():
                return [TextContent(type="text", text=f"Error: Not a file: {path}")]
            content = path.read_text(encoding="utf-8")
            return [TextContent(type="text", text=content)]

        elif name == "write_file":
            path = Path(arguments["path"])
            content = arguments["content"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return [TextContent(type="text", text=f"Successfully wrote to {path}")]

        elif name == "list_directory":
            path = Path(arguments["path"])
            if not path.exists():
                return [TextContent(type="text", text=f"Error: Directory not found: {path}")]
            if not path.is_dir():
                return [TextContent(type="text", text=f"Error: Not a directory: {path}")]
            entries = []
            for entry in sorted(path.iterdir()):
                entry_type = "DIR" if entry.is_dir() else "FILE"
                entries.append(f"[{entry_type}] {entry.name}")
            result = "\n".join(entries) if entries else "(empty directory)"
            return [TextContent(type="text", text=result)]

        elif name == "create_directory":
            path = Path(arguments["path"])
            path.mkdir(parents=True, exist_ok=True)
            return [TextContent(type="text", text=f"Successfully created directory: {path}")]

        elif name == "delete_file":
            path = Path(arguments["path"])
            if not path.exists():
                return [TextContent(type="text", text=f"Error: File not found: {path}")]
            if not path.is_file():
                return [TextContent(type="text", text=f"Error: Not a file: {path}")]
            path.unlink()
            return [TextContent(type="text", text=f"Successfully deleted: {path}")]

        elif name == "file_info":
            path = Path(arguments["path"])
            if not path.exists():
                return [TextContent(type="text", text=f"Error: Path not found: {path}")]
            stat = path.stat()
            info = [
                f"Path: {path.absolute()}",
                f"Type: {'Directory' if path.is_dir() else 'File'}",
                f"Size: {stat.st_size} bytes",
                f"Modified: {stat.st_mtime}",
            ]
            return [TextContent(type="text", text="\n".join(info))]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_sse(request: Request):
    """Handle SSE connections from MCP clients."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )


async def handle_messages(request: Request):
    """Handle POST messages from MCP clients."""
    await sse.handle_post_message(request.scope, request.receive, request._send)


async def health_check(request: Request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "server": "mcp-file-server"})


routes = [
    Route("/sse", endpoint=handle_sse),
    Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    Route("/health", endpoint=health_check),
]

app = Starlette(debug=True, routes=routes)


def main():
    """Main entry point - runs the SSE server."""
    print("Starting MCP File Server (SSE mode)")
    print("SSE endpoint: http://localhost:8000/sse")
    print("Messages endpoint: http://localhost:8000/messages/")
    print("Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
