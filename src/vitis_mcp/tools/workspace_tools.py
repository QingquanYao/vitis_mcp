"""工作空间工具：list_components / get_build_log / run_python_script。"""

from mcp.server.fastmcp import Context

from vitis_mcp.python_utils import safe_repr, to_posix_path, validate_identifier
from vitis_mcp.server import _NO_SESSION, _require_session, _safe_execute, mcp


@mcp.tool()
async def list_components(
    workspace: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """列出工作空间中所有组件（平台、应用等）。

    Args:
        workspace: 工作空间路径。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comps = client.list_components()\n"
        f"print('Components:', comps)\n"
    )
    return await _safe_execute(session, code, 60.0, "list_components")


@mcp.tool()
async def get_build_log(
    workspace: str,
    app_name: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """读取应用程序的编译日志（只返回 error/warning 行）。

    Args:
        workspace: 工作空间路径。
        app_name: 应用名称。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(app_name, "app_name")

    code = (
        f"import os, glob\n"
        f"log_pattern = os.path.join({safe_repr(to_posix_path(workspace))}, "
        f"{safe_repr(app_name)}, '**', '*.log')\n"
        f"logs = glob.glob(log_pattern, recursive=True)\n"
        f"found = False\n"
        f"for log_file in logs:\n"
        f"    with open(log_file, 'r', errors='replace') as f:\n"
        f"        for line in f:\n"
        f"            if any(k in line.lower() for k in ['error', 'warning', 'fatal']):\n"
        f"                print(line, end='')\n"
        f"                found = True\n"
        f"if not found:\n"
        f"    print('No errors or warnings found in build logs.')\n"
    )
    return await _safe_execute(session, code, 60.0, "get_build_log")


@mcp.tool()
async def run_python_script(
    code: str,
    session_id: str = "default",
    timeout: int = 120,
    ctx: Context = None,
) -> str:
    """执行任意 Vitis Python API 代码（高级/自定义用途）。

    代码将在 Vitis Python REPL 中执行，可使用 vitis、xsdb、hsi 等模块。
    适用于工具未覆盖的高级操作。

    Args:
        code: 要执行的 Python 代码字符串。
        session_id: 会话标识符。
        timeout: 执行超时秒数，默认 120。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    return await _safe_execute(session, code, float(timeout), "run_python_script")
