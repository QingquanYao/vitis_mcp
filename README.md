# Vitis MCP Server

> Let Claude build, debug, and deploy your FPGA embedded software.

**Vitis MCP** is a [Model Context Protocol](https://modelcontextprotocol.io/) server that gives AI assistants (Claude, etc.) full control over [AMD Vitis Unified IDE](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html) -- from creating platforms and applications to programming FPGAs and debugging processors over JTAG.

**Vitis MCP** 是一个 MCP 服务器，让 AI 助手（Claude 等）能够完整控制 AMD Vitis Unified IDE -- 从创建平台和应用，到 FPGA 编程和处理器 JTAG 调试。

---

## Features / 特性

- **Persistent Session** -- Launches a `vitis -i` Python REPL that stays alive across tool calls. No more 30-second startup per command.
- **28 Tools** -- Covers the full embedded workflow: platform creation, app build, BSP config, FPGA programming, memory/register access, and more.
- **Unified Architecture** -- Both project management (`import vitis`) and hardware debugging (`import xsdb`) run in a single Python session.
- **Safe by Design** -- Commands are base64-encoded with a sentinel protocol. User parameters are `repr()`-quoted, never interpolated into raw code strings.
- **Multi-Session** -- Run multiple independent Vitis instances in parallel via `session_id`.

---

## Quick Start / 快速开始

### 1. Install / 安装

```bash
# Clone and install
git clone https://github.com/QingquanYao/vitis_mcp.git
cd vitis_mcp
pip install -e .
```

**Requirements / 依赖：**
- Python >= 3.10
- AMD Vitis Unified IDE 2023.2+ (tested on 2024.2)
- `mcp` Python package (auto-installed)

### 2. Configure / 配置

Add to your Claude Code settings or Claude Desktop config:

将以下内容添加到 Claude Code 设置或 Claude Desktop 配置中：

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
>
> 如果 `vitis` 已在系统 PATH 中，`VITIS_PATH` 可省略。

### 3. Use / 使用

Just ask Claude in natural language:

直接用自然语言和 Claude 对话即可：

```
"Create a standalone platform from design_wrapper.xsa for Cortex-A53"
"Build the hello_world app and download it to the board"
"Read memory at 0xFF000000, 16 words"
```

---

## Tools / 工具列表

### Project Management / 工程管理

| Tool | Description |
|------|-------------|
| `start_session` | Start a persistent Vitis Python REPL / 启动持久化 Vitis Python 会话 |
| `create_platform` | Create platform from XSA and build BSP / 从 XSA 创建平台并编译 BSP |
| `get_platform_info` | Query platform details / 查询平台信息 |
| `create_app` | Create bare-metal/FreeRTOS/Linux app / 创建应用程序 |
| `import_sources` | Import C/C++ source files / 导入源文件 |
| `set_bsp_config` | Modify BSP parameters / 修改 BSP 参数 |
| `add_library` | Add software library (lwip, xilpm, ...) / 添加软件库 |
| `build_app` | Compile application / 编译应用 |
| `clean_app` | Clean build artifacts / 清理构建产物 |
| `list_components` | List workspace components / 列出工作空间组件 |
| `get_build_log` | Extract errors/warnings from build log / 提取编译日志中的错误和警告 |
| `run_python_script` | Execute arbitrary Vitis Python code / 执行任意 Vitis Python 代码 |

### Hardware Debug / 硬件调试

| Tool | Description |
|------|-------------|
| `hw_connect` | Connect to JTAG / hw_server / 连接 JTAG 调试器 |
| `hw_list_targets` | List all debug targets / 列出所有调试目标 |
| `hw_select_target` | Select target by ID / 选择目标处理器 |
| `hw_program_fpga` | Download bitstream to FPGA / 下载比特流到 FPGA |
| `hw_program_elf` | Program ELF and optionally run / 烧录 ELF 并运行 |
| `hw_stop` | Halt processor / 停止处理器 |
| `hw_continue` | Resume execution / 继续执行 |
| `hw_step` | Step over / 单步执行 |
| `hw_read_memory` | Read target memory / 读取内存 |
| `hw_write_memory` | Write target memory / 写入内存 |
| `hw_read_register` | Read register group / 读取寄存器组 |
| `hw_backtrace` | Get call stack / 获取调用栈 |
| `hw_disconnect` | Close debug session / 断开调试连接 |
| `run_xsdb_command` | Execute arbitrary xsdb Python code / 执行任意 xsdb 命令 |

### Session Management / 会话管理

| Tool | Description |
|------|-------------|
| `stop_session` | Close a Vitis session / 关闭会话 |
| `list_sessions` | List all active sessions / 列出所有活跃会话 |

---

## Architecture / 架构

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

**哨兵协议：** 每条命令经 base64 编码后，包裹在 `try/except` 中，并以唯一的 `<<<VMCP_xxxx_RC=N>>>` 标记结束。会话逐行读取 stdout 直到匹配标记，确保无论命令多复杂都能可靠地收集输出。

---

## Works with Vivado MCP / 与 Vivado MCP 协同

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

## Project Structure / 项目结构

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

## License / 许可

MIT
