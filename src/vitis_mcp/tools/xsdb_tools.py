"""XSDB 硬件调试工具：通过 Python xsdb 模块执行调试操作。

Vitis 2024.2 提供 Python xsdb 模块，可在 vitis -i REPL 中直接调试。
所有工具通过 session.execute() 发送 Python 代码到 Vitis REPL。
"""

from mcp.server.fastmcp import Context

from vitis_mcp.python_utils import (
    safe_repr,
    to_posix_path,
    validate_address,
)
from vitis_mcp.server import _NO_SESSION, _require_session, _safe_execute, mcp

# XSDB 会话初始化代码（在 Vitis REPL 中首次调用时执行）
_XSDB_INIT = (
    "import xsdb\n"
    "if '_xsdb_session' not in dir():\n"
    "    _xsdb_session = None\n"
)

_XSDB_ENSURE = (
    "if _xsdb_session is None:\n"
    "    raise RuntimeError('XSDB 未连接。请先调用 hw_connect。')\n"
)


@mcp.tool()
async def hw_connect(
    hw_server_url: str = "TCP:localhost:3121",
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """连接 JTAG 调试器 / hw_server。

    建立 XSDB 调试会话并连接到硬件服务器。

    Args:
        hw_server_url: hw_server 地址，默认 TCP:localhost:3121。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"_xsdb_session = xsdb.start_debug_session()\n"
        f"result = _xsdb_session.connect(url={safe_repr(hw_server_url)})\n"
        f"print('Connected:', result)\n"
    )
    return await _safe_execute(session, code, 30.0, "hw_connect")


@mcp.tool()
async def hw_list_targets(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """列出所有 JTAG 目标（处理器、PL 等）。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"result = _xsdb_session.targets()\n"
        f"print(result)\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_list_targets")


@mcp.tool()
async def hw_select_target(
    target_id: int,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """选择调试目标（按 ID）。

    使用 hw_list_targets 查看可用目标及其 ID。

    Args:
        target_id: 目标编号（从 hw_list_targets 输出中获取）。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.target({int(target_id)})\n"
        f"print('Target selected:', {int(target_id)})\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_select_target")


@mcp.tool()
async def hw_program_fpga(
    bitfile_path: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """下载比特流到 FPGA/PL。

    Args:
        bitfile_path: 比特流文件路径（.bit）。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.fpga(file={safe_repr(to_posix_path(bitfile_path))})\n"
        f"print('FPGA programmed successfully')\n"
    )
    return await _safe_execute(session, code, 60.0, "hw_program_fpga")


@mcp.tool()
async def hw_program_elf(
    elf_path: str,
    target_id: int = 0,
    auto_run: bool = True,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """烧录 ELF 文件到处理器并可选自动运行。

    Args:
        elf_path: ELF 文件路径。
        target_id: 目标处理器 ID（0 表示使用当前已选目标）。
        auto_run: 烧录后是否自动运行，默认 True。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    select_cmd = ""
    if target_id > 0:
        select_cmd = f"_xsdb_session.target({int(target_id)})\n"

    run_cmd = "_xsdb_session.con()\nprint('Execution started')\n" if auto_run else ""

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"{select_cmd}"
        f"_xsdb_session.dow(file={safe_repr(to_posix_path(elf_path))})\n"
        f"print('ELF downloaded successfully')\n"
        f"{run_cmd}"
    )
    return await _safe_execute(session, code, 60.0, "hw_program_elf")


@mcp.tool()
async def hw_stop(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """停止目标处理器执行。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.stop()\n"
        f"print('Target stopped')\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_stop")


@mcp.tool()
async def hw_continue(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """继续执行目标处理器。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.con()\n"
        f"print('Execution continued')\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_continue")


@mcp.tool()
async def hw_step(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """单步执行（step over）。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.nxt()\n"
        f"print('Step completed')\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_step")


@mcp.tool()
async def hw_read_memory(
    address: str,
    length: int = 1,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """读取目标内存。

    Args:
        address: 起始地址（十六进制，如 0xFF000000）。
        length: 读取字数，默认 1。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_address(address, "address")

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"result = _xsdb_session.mrd({address}, {int(length)})\n"
        f"print(result)\n"
    )
    return await _safe_execute(session, code, 30.0, "hw_read_memory")


@mcp.tool()
async def hw_write_memory(
    address: str,
    value: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """写入目标内存。

    Args:
        address: 目标地址（十六进制，如 0xFF000000）。
        value: 写入值（十六进制，如 0xDEADBEEF）。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_address(address, "address")
    validate_address(value, "value")

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"_xsdb_session.mwr({address}, {value})\n"
        f"print('Memory written')\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_write_memory")


@mcp.tool()
async def hw_read_register(
    reg_group: str = "",
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """读取寄存器组。

    Args:
        reg_group: 寄存器组名称（如 crl_apb、ddrc）。留空列出所有组。
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    if reg_group:
        rrd_arg = safe_repr(reg_group)
    else:
        rrd_arg = ""

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"result = _xsdb_session.rrd({rrd_arg})\n"
        f"print(result)\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_read_register")


@mcp.tool()
async def hw_backtrace(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """获取当前调用栈（backtrace）。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"{_XSDB_ENSURE}"
        f"result = _xsdb_session.bt()\n"
        f"print(result)\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_backtrace")


@mcp.tool()
async def hw_disconnect(
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """断开 JTAG 连接并关闭调试会话。

    Args:
        session_id: Vitis 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"{_XSDB_INIT}"
        f"if _xsdb_session is not None:\n"
        f"    _xsdb_session.disconnect()\n"
        f"    _xsdb_session = None\n"
        f"    print('XSDB session closed')\n"
        f"else:\n"
        f"    print('No active XSDB session')\n"
    )
    return await _safe_execute(session, code, 15.0, "hw_disconnect")


@mcp.tool()
async def run_xsdb_command(
    command: str,
    session_id: str = "default",
    timeout: int = 30,
    ctx: Context = None,
) -> str:
    """执行任意 XSDB Python 命令（高级/自定义用途）。

    代码在 Vitis Python REPL 中执行，可使用 _xsdb_session 变量
    访问已建立的调试会话（需先调用 hw_connect）。

    Args:
        command: 要执行的 Python 代码（可使用 _xsdb_session 变量）。
        session_id: Vitis 会话标识符。
        timeout: 执行超时秒数，默认 30。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = f"{_XSDB_INIT}{command}\n"
    return await _safe_execute(session, code, float(timeout), "run_xsdb_command")
