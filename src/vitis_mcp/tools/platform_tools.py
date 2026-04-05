"""平台管理工具：create_platform / get_platform_info。"""

from mcp.server.fastmcp import Context

from vitis_mcp.python_utils import safe_repr, to_posix_path, validate_identifier
from vitis_mcp.server import _NO_SESSION, _require_session, _safe_execute, mcp


@mcp.tool()
async def create_platform(
    workspace: str,
    xsa_path: str,
    platform_name: str,
    cpu: str,
    os_type: str = "standalone",
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """从 XSA 文件创建 Vitis 硬件平台并编译 BSP。

    Args:
        workspace: 工作空间路径。
        xsa_path: XSA 硬件描述文件路径。
        platform_name: 平台名称。
        cpu: CPU 核心，如 psu_cortexa53_0、ps7_cortexa9_0。
        os_type: 操作系统：standalone / freertos / linux，默认 standalone。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(platform_name, "platform_name")
    validate_identifier(cpu, "cpu")
    validate_identifier(os_type, "os_type")

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"plat = client.create_platform_component(\n"
        f"    name={safe_repr(platform_name)},\n"
        f"    hw_design={safe_repr(to_posix_path(xsa_path))},\n"
        f"    cpu={safe_repr(cpu)},\n"
        f"    os={safe_repr(os_type)}\n"
        f")\n"
        f"plat = client.get_platform_component({safe_repr(platform_name)})\n"
        f"status = plat.build()\n"
        f"print('Platform build status:', status)\n"
    )
    return await _safe_execute(session, code, 600.0, "create_platform")


@mcp.tool()
async def get_platform_info(
    workspace: str,
    platform_name: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """获取平台信息（处理器列表、域信息等）。

    Args:
        workspace: 工作空间路径。
        platform_name: 平台名称。
        session_id: 会话标识符。
    """
    session = _require_session(ctx, session_id)
    if not session:
        return _NO_SESSION.format(sid=session_id)

    validate_identifier(platform_name, "platform_name")

    code = (
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"plat = client.get_platform_component({safe_repr(platform_name)})\n"
        f"print(plat.report())\n"
    )
    return await _safe_execute(session, code, 60.0, "get_platform_info")
