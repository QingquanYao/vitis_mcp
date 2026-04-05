# Vitis MCP Server

> Let Claude build, debug, and deploy your FPGA embedded software.

[**中文文档**](README_zh.md)

**Vitis MCP** is a [Model Context Protocol](https://modelcontextprotocol.io/) server that gives AI assistants (Claude, etc.) full control over [AMD Vitis Unified IDE](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html) -- from creating platforms and applications to programming FPGAs and debugging processors over JTAG.

---

## Features

- **Persistent Session** -- Launches a `vitis -i` Python REPL that stays alive across tool calls. No more 30-second startup per command.
- **28 Tools** -- Covers the full embedded workflow: platform creation, app build, BSP config, FPGA programming, memory/register access, and more.
- **Unified Architecture** -- Both project management (`import vitis`) and hardware debugging (`import xsdb`) run in a single Python session.
- **Safe by Design** -- Commands are base64-encoded with a sentinel protocol. User parameters are `repr()`-quoted, never interpolated into raw code strings.
- **Multi-Session** -- Run multiple independent Vitis instances in parallel via `session_id`.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/QingquanYao/vitis_mcp.git
cd vitis_mcp
pip install -e .
```

**Requirements:**
- Python >= 3.10
- AMD Vitis Unified IDE 2023.2+ (tested on 2024.2)
- `mcp` Python package (auto-installed)

### 2. Configure

Add to your Claude Code settings or Claude Desktop config:

```json
{
  "mcpServers": {
    "vitis": {
      "command": "python",
      "args": ["-m", "vitis_mcp"],
      "env": {
        "VITIS_PATH": "C:\\Xilinx\\Vitis\\2024.2\\bin\\vitis.bat"
      }
    }
  }
}
```

> `VITIS_PATH` is optional if `vitis` is already on your system PATH.

### 3. Use

Just ask Claude in natural language:

```
"Create a standalone platform from design_wrapper.xsa for Cortex-A53"
"Build the hello_world app and download it to the board"
"Read memory at 0xFF000000, 16 words"
```

---

## Tools

### Project Management

| Tool | Description |
|------|-------------|
| `start_session` | Start a persistent Vitis Python REPL |
| `create_platform` | Create platform from XSA and build BSP |
| `get_platform_info` | Query platform details (processors, domains) |
| `create_app` | Create bare-metal / FreeRTOS / Linux application |
| `import_sources` | Import C/C++ source files into application |
| `set_bsp_config` | Modify BSP parameters |
| `add_library` | Add software library (lwip, xilpm, ...) |
| `build_app` | Compile application, return ELF path |
| `clean_app` | Clean build artifacts |
| `list_components` | List all workspace components |
| `get_build_log` | Extract errors/warnings from build log |
| `run_python_script` | Execute arbitrary Vitis Python API code |

### Hardware Debug

| Tool | Description |
|------|-------------|
| `hw_connect` | Connect to JTAG / hw_server |
| `hw_list_targets` | List all debug targets |
| `hw_select_target` | Select target processor by ID |
| `hw_program_fpga` | Download bitstream to FPGA |
| `hw_program_elf` | Program ELF and optionally run |
| `hw_stop` | Halt processor execution |
| `hw_continue` | Resume execution |
| `hw_step` | Step over (single step) |
| `hw_read_memory` | Read target memory |
| `hw_write_memory` | Write target memory |
| `hw_read_register` | Read register group |
| `hw_backtrace` | Get call stack |
| `hw_disconnect` | Close debug session |
| `run_xsdb_command` | Execute arbitrary xsdb Python code |

### Session Management

| Tool | Description |
|------|-------------|
| `stop_session` | Close a Vitis session |
| `list_sessions` | List all active sessions |

---

## Architecture

```
Claude ──(stdio/MCP)──> FastMCP Server
                             │
                       SessionManager
                       ├─ "default" ──> vitis -i  (Python REPL)
                       │                ├─ import vitis   (project mgmt)
                       │                └─ import xsdb    (hw debug)
                       └─ "worker2" ──> vitis -i  (independent)
```

**Sentinel Protocol:** Each command is base64-encoded, wrapped in `try/except`, and terminated with a unique `<<<VMCP_xxxx_RC=N>>>` marker. The session reads stdout line-by-line until it matches the marker, ensuring reliable output collection regardless of command complexity.

---

## Works with Vivado MCP

```
Vivado MCP                              Vitis MCP
  [HDL Design]                            [Embedded Software]
       │                                       │
  run_synthesis ──> run_implementation    create_platform
       │                                       │
  generate_bitstream ──> export XSA ───> create_app ──> build_app
                                               │
                                         hw_program_fpga
                                               │
                                         hw_program_elf
```

---

## Project Structure

```
src/vitis_mcp/
├── __main__.py          # Entry point: python -m vitis_mcp
├── config.py            # Auto-detect Vitis installation
├── server.py            # FastMCP instance + SessionManager
├── session.py           # VitisSession (async subprocess)
├── python_utils.py      # Sentinel protocol + safety utils
└── tools/
    ├── session_tools.py     # start/stop/list sessions
    ├── platform_tools.py    # Platform creation & info
    ├── app_tools.py         # App create/build/clean
    ├── bsp_tools.py         # BSP config & libraries
    ├── workspace_tools.py   # Components & build logs
    └── xsdb_tools.py        # All hardware debug tools
```

---

## License

MIT
