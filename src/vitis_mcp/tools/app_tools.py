"""应用管理工具：create_app / build_app / clean_app。"""

from mcp.server.fastmcp import Context

from vitis_mcp.python_utils import safe_repr, to_posix_path, validate_identifier
from vitis_mcp.server import _NO_SESSION, _require_session, _safe_execute, mcp


@mcp.tool()
async def create_app(
    workspace: str,
    app_name: str,
    platform_xpfm: str,
    domain: str,
    template: str = "hello_world",
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """创建裸机/FreeRTOS/Linux 应用程序组件。

    Args:
        workspace: 工作空间路径。
        app_name: 应用名称。
        platform_xpfm: .xpfm 平台文件路径（平台编译后生成）。
        domain: 域名称（如 standalone_a53）。
        template: 模板名称：hello_world / empty_application / freertos_hello_world 等。
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
        f"comp = client.create_app_component(\n"
        f"    name={safe_repr(app_name)},\n"
        f"    platform={safe_repr(to_posix_path(platform_xpfm))},\n"
        f"    domain={safe_repr(domain)},\n"
        f"    template={safe_repr(template)}\n"
        f")\n"
        f"print('App created:', comp)\n"
    )
    return await _safe_execute(session, code, 120.0, "create_app")


@mcp.tool()
async def build_app(
    workspace: str,
    app_name: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """编译应用程序，返回编译状态和 ELF 路径。

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
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comp = client.get_component(name={safe_repr(app_name)})\n"
        f"status = comp.build()\n"
        f"print('Build status:', status)\n"
    )
    return await _safe_execute(session, code, 600.0, "build_app")


@mcp.tool()
async def clean_app(
    workspace: str,
    app_name: str,
    session_id: str = "default",
    ctx: Context = None,
) -> str:
    """清理应用程序构建产物。

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
        f"import vitis\n"
        f"client = vitis.create_client()\n"
        f"client.set_workspace(path={safe_repr(to_posix_path(workspace))})\n"
        f"comp = client.get_component(name={safe_repr(app_name)})\n"
        f"comp.clean()\n"
        f"print('Clean done')\n"
    )
    return await _safe_execute(session, code, 120.0, "clean_app")
