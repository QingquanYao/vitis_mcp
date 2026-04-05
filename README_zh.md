# Vitis MCP Server

> 让 Claude 帮你构建、调试、部署 FPGA 嵌入式软件。

[**English**](README.md)

**Vitis MCP** 是一个 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 服务器，让 AI 助手（Claude 等）能够完整控制 [AMD Vitis Unified IDE](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html) —— 从创建平台和应用，到 FPGA 编程和处理器 JTAG 调试，全流程自动化。

---

## 特性

- **持久化会话** —— 启动一个 `vitis -i` Python REPL 长驻进程，跨工具调用保持状态。告别每次命令 30 秒的启动等待。
- **28 个工具** —— 覆盖完整嵌入式开发流程：平台创建、应用编译、BSP 配置、FPGA 编程、内存/寄存器读写等。
- **统一架构** —— 项目管理（`import vitis`）和硬件调试（`import xsdb`）在同一个 Python 会话中运行，无需切换。
- **安全设计** —— 命令经 base64 编码 + 哨兵协议传输，用户参数通过 `repr()` 安全引用，杜绝代码注入。
- **多会话支持** —— 通过 `session_id` 同时运行多个独立的 Vitis 实例。

---

## 快速开始

### 1. 安装

```bash
git clone https://github.com/QingquanYao/vitis_mcp.git
cd vitis_mcp
pip install -e .
```

**环境要求：**
- Python >= 3.10
- AMD Vitis Unified IDE 2023.2+（已在 2024.2 上测试）
- `mcp` Python 包（自动安装）

### 2. 配置

将以下内容添加到 Claude Code 设置或 Claude Desktop 配置文件中：

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

> 如果 `vitis` 已在系统 PATH 中，`VITIS_PATH` 可省略，服务器会自动检测。

### 3. 使用

直接用自然语言和 Claude 对话：

```
"用 design_wrapper.xsa 为 Cortex-A53 创建一个 standalone 平台"
"编译 hello_world 应用并下载到板子上"
"读取 0xFF000000 地址的内存，读 16 个字"
```

---

## 工具列表

### 工程管理

| 工具 | 说明 |
|------|------|
| `start_session` | 启动持久化 Vitis Python 会话 |
| `create_platform` | 从 XSA 创建硬件平台并编译 BSP |
| `get_platform_info` | 查询平台信息（处理器、域等） |
| `create_app` | 创建裸机 / FreeRTOS / Linux 应用程序 |
| `import_sources` | 向应用导入 C/C++ 源文件 |
| `set_bsp_config` | 修改 BSP 配置参数 |
| `add_library` | 添加软件库（lwip、xilpm 等） |
| `build_app` | 编译应用程序，返回 ELF 路径 |
| `clean_app` | 清理构建产物 |
| `list_components` | 列出工作空间中所有组件 |
| `get_build_log` | 提取编译日志中的错误和警告 |
| `run_python_script` | 执行任意 Vitis Python API 代码 |

### 硬件调试

| 工具 | 说明 |
|------|------|
| `hw_connect` | 连接 JTAG 调试器 / hw_server |
| `hw_list_targets` | 列出所有调试目标 |
| `hw_select_target` | 按 ID 选择目标处理器 |
| `hw_program_fpga` | 下载比特流到 FPGA |
| `hw_program_elf` | 烧录 ELF 文件并可选自动运行 |
| `hw_stop` | 停止处理器执行 |
| `hw_continue` | 继续执行 |
| `hw_step` | 单步执行（Step Over） |
| `hw_read_memory` | 读取目标内存 |
| `hw_write_memory` | 写入目标内存 |
| `hw_read_register` | 读取寄存器组 |
| `hw_backtrace` | 获取当前调用栈 |
| `hw_disconnect` | 断开调试连接 |
| `run_xsdb_command` | 执行任意 xsdb Python 命令 |

### 会话管理

| 工具 | 说明 |
|------|------|
| `stop_session` | 关闭指定 Vitis 会话 |
| `list_sessions` | 列出所有活跃会话 |

---

## 架构

```
Claude ──(stdio/MCP)──> FastMCP 服务器
                             │
                        SessionManager（会话管理器）
                        ├─ "default" ──> vitis -i  (Python REPL)
                        │                ├─ import vitis   (工程管理)
                        │                └─ import xsdb    (硬件调试)
                        └─ "worker2" ──> vitis -i  (独立实例)
```

**哨兵协议：** 每条命令经 base64 编码后，包裹在 `try/except` 中，并以唯一的 `<<<VMCP_xxxx_RC=N>>>` 标记结束。会话逐行读取 stdout 直到匹配标记，确保无论命令多复杂都能可靠地收集输出。

---

## 与 Vivado MCP 协同

```
Vivado MCP                              Vitis MCP
  [硬件设计]                               [嵌入式软件]
       │                                       │
  综合 ──> 实现                          创建平台
       │                                       │
  生成比特流 ──> 导出 XSA ─────────> 创建应用 ──> 编译应用
                                               │
                                          下载比特流
                                               │
                                          烧录 ELF
```

---

## 项目结构

```
src/vitis_mcp/
├── __main__.py          # 入口：python -m vitis_mcp
├── config.py            # 自动检测 Vitis 安装路径
├── server.py            # FastMCP 实例 + 会话管理器
├── session.py           # VitisSession（异步子进程管理）
├── python_utils.py      # 哨兵协议 + 安全工具函数
└── tools/
    ├── session_tools.py     # 会话启动/停止/列出
    ├── platform_tools.py    # 平台创建与查询
    ├── app_tools.py         # 应用创建/编译/清理
    ├── bsp_tools.py         # BSP 配置与库管理
    ├── workspace_tools.py   # 组件列表与编译日志
    └── xsdb_tools.py        # 全部硬件调试工具
```

---

## 许可证

MIT
