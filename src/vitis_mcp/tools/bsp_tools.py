"""BSP 配置工具：import_sources / set_bsp_config / add_library。"""

from mcp.server.fastmcp import Context

from vitis_mcp.python_utils import safe_repr, to_posix_path, validate_identifier
from vitis_mcp.server import _NO_SESSION, _require_session, _safe_execute, mcp


@mcp.tool()
async def import_sources(
    workspace: str,
    app_name: str,
    src_dir: str,
    files: str = "",
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """向应用程序导入 C/C++ 源文件。

    Args:
        workspace: 工作空间路径。
        app_name: 应用名称。
        src_dir: 源文件所在目录。
        files: 可选，要导入的文件名列表（逗号分隔，如 "main.c,uart.c"）。留空导入整个目录。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(app_name, "app_name")

    if files:
        file_list = [f.strip() for f in files.split(",") if f.strip()]
        files_arg = f"    files={safe_repr(file_list)},\n"
    else:
        files_arg = ""

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comp = client.get_component(name={safe_repr(app_name)})\n"
        f"comp.import_files(\n"
        f"    from_loc={safe_repr(to_posix_path(src_dir))},\n"
        f"{files_arg}"
        f"    dest_dir_in_cmp='src'\n"
        f")\n"
        f"print('Sources imported successfully')\n"
    )
    return await _safe_execute(session, code, 60.0, "import_sources")


@mcp.tool()
async def set_bsp_config(
    workspace: str,
    app_name: str,
    lib_name: str,
    key: str,
    value: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """修改 BSP/库配置参数。

    通过 domain.set_config() 修改 BSP 参数。

    Args:
        workspace: 工作空间路径。
        app_name: 应用名称（平台组件名）。
        lib_name: 配置选项类型，如 os / lib / driver。
        key: 参数键名。
        value: 参数值。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(app_name, "app_name")

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comp = client.get_component(name={safe_repr(app_name)})\n"
        f"comp.set_lib_parameter(\n"
        f"    lib={safe_repr(lib_name)},\n"
        f"    key={safe_repr(key)},\n"
        f"    value={safe_repr(value)}\n"
        f")\n"
        f"print('BSP config updated')\n"
    )
    return await _safe_execute(session, code, 60.0, "set_bsp_config")


@mcp.tool()
async def add_library(
    workspace: str,
    app_name: str,
    lib_name: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """向应用程序添加软件库（如 lwip、xilpm、xilffs）。

    Args:
        workspace: 工作空间路径。
        app_name: 应用名称。
        lib_name: 库名称。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(app_name, "app_name")

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comp = client.get_component(name={safe_repr(app_name)})\n"
        f"comp.add_library({safe_repr(lib_name)})\n"
        f"print('Library added:', {safe_repr(lib_name)})\n"
    )
    return await _safe_execute(session, code, 60.0, "add_library")
