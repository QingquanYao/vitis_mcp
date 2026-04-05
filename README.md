# Vitis Unified MCP Server

支持 Vitis Unified IDE (2023.2+) 全工作流自动化的 MCP Server。

---

## 文件说明

```
vitis_mcp/
├── vitis_mcp_server.py      ← MCP Server 主程序
├── mock_vitis.py            ← 离线测试用的 Vitis 模拟器
├── test_vitis_mcp.py        ← 四层测试套件
├── claude_desktop_config.json  ← Claude Desktop 配置参考
└── README.md
```

---

## 快速开始

### 1. 配置路径

编辑 `vitis_mcp_server.py` 顶部，或设置环境变量：

```powershell
$env:VITIS_VERSION = "2024.2"       # 按实际版本修改
$env:XILINX_ROOT   = "C:\Xilinx"
```

### 2. 测试（离线，不需要 Vitis）

```powershell
cd D:\vitis_mcp

# Layer 1：协议测试
python test_vitis_mcp.py --layer 1

# Layer 2：Mock 测试（完整工程流程）
python test_vitis_mcp.py --layer 2 --mock

# 两层一起跑
python test_vitis_mcp.py --layer 2 --mock --workspace C:\temp\vitis_test
```

### 3. 测试（真实 Vitis，无硬件）

```powershell
python test_vitis_mcp.py --layer 3 --xsa C:\my_project\design.xsa
```

### 4. 测试（有板子）

```powershell
python test_vitis_mcp.py --layer 4 `
    --xsa     C:\my_project\design.xsa `
    --bitfile  C:\my_project\design.bit `
    --elf      C:\my_project\app.elf `
    --hw-server TCP:localhost:3121
```

---

## 接入 Claude Desktop

将 `claude_desktop_config.json` 的内容合并到：
```
%APPDATA%\Claude\claude_desktop_config.json
```

重启 Claude Desktop，左下角应出现 🔌 vitis 工具标志。

---

## 支持的工具

### 工程管理（Vitis Python API）

| 工具 | 说明 |
|------|------|
| `create_platform` | 从 XSA 创建硬件平台并编译 BSP |
| `get_platform_info` | 读取平台信息（处理器、域等） |
| `create_app` | 创建裸机/FreeRTOS 应用 |
| `import_sources` | 导入 C/C++ 源文件 |
| `set_bsp_config` | 修改 BSP/库参数 |
| `add_library` | 添加软件库（lwip、xilpm 等） |
| `build_app` | 编译应用，返回 ELF 路径 |
| `clean_app` | 清理构建产物 |
| `list_components` | 列出工作空间所有组件 |
| `get_build_log` | 读取编译错误/警告 |
| `run_python_script` | 执行任意 Vitis Python API 代码 |

### 硬件调试（XSDB/Tcl，持久会话）

| 工具 | 说明 |
|------|------|
| `hw_connect` | 连接 JTAG / hw_server |
| `hw_list_targets` | 列出所有目标 |
| `hw_select_target` | 选择目标处理器 |
| `hw_program_fpga` | 下载比特流 |
| `hw_program_elf` | 烧录 ELF 并运行 |
| `hw_stop` / `hw_continue` | 停止/继续执行 |
| `hw_step` | 单步执行 |
| `hw_read_memory` | 读内存 |
| `hw_write_memory` | 写内存 |
| `hw_read_register` | 读寄存器组 |
| `hw_backtrace` | 获取调用栈 |
| `hw_disconnect` | 断开连接 |
| `run_xsdb_command` | 执行任意 XSDB/Tcl 命令 |

---

## 与 Vivado MCP 协同

```
Vivado MCP                         Vitis MCP
[HDL修改] → [综合实现] → [导出XSA] → [create_platform] → [create_app]
                                   → [build_app]        → [hw_program_fpga]
                                                        → [hw_program_elf]
```

---

## 日志

运行时日志写入 `vitis_mcp.log`（与 server 同目录），`DEBUG` 级别，
记录所有请求/响应及 XSDB 交互，方便排查问题。
