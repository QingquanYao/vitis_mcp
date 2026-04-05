"""FastMCP 服务器实例、lifespan 管理、SessionManager、工具注册。

架构：
  Claude Code ──(stdio)──> FastMCP Server
                                │
                          SessionManager (lifespan context)
                          ├─ "default" ──> vitis -i (Python REPL)
                          └─ ...
"""

import json
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from vitis_mcp.config import find_vitis
from vitis_mcp.session import VitisSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 模块级 SessionManager 引用，供 Resources 使用
_manager_ref: "SessionManager | None" = None

# session_id 格式验证
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _validate_session_id(session_id: str) -> str:
    if not _SESSION_ID_RE.match(session_id):
        raise ValueError(
            f"session_id 格式非法: {session_id!r}。"
            f"仅允许字母、数字、下划线、连字符，长度 1~64。"
        )
    return session_id


# --------------------------------------------------------------------------- #
#  SessionManager
# --------------------------------------------------------------------------- #

class SessionManager:
    """管理多个 Vitis 会话实例。"""

    def __init__(self, vitis_path: str):
        self._default_vitis_path = vitis_path
        self._sessions: dict[str, VitisSession] = {}

    @property
    def default_vitis_path(self) -> str:
        return self._default_vitis_path

    def get(self, session_id: str) -> VitisSession | None:
        _validate_session_id(session_id)
        session = self._sessions.get(session_id)
        if session and not session.is_alive:
            logger.warning("会话 '%s' 进程已死，自动清理。", session_id)
            del self._sessions[session_id]
            return None
        return session

    async def start_session(
        self,
        session_id: str = "default",
        vitis_path: str | None = None,
        timeout: float = 120.0,
    ) -> tuple[VitisSession, str]:
        _validate_session_id(session_id)
        existing = self.get(session_id)
        if existing:
            return existing, f"会话 '{session_id}' 已在运行中。"

        path = vitis_path or self._default_vitis_path
        session = VitisSession(vitis_path=path, session_id=session_id)
        banner = await session.start(timeout=timeout)
        self._sessions[session_id] = session
        return session, banner

    async def stop_session(self, session_id: str) -> str:
        session = self._sessions.pop(session_id, None)
        if not session:
            return f"会话 '{session_id}' 不存在。"
        await session.stop()
        return f"会话 '{session_id}' 已关闭。"

    async def close_all(self) -> None:
        session_ids = list(self._sessions.keys())
        for sid in session_ids:
            session = self._sessions.pop(sid, None)
            if session:
                try:
                    await session.stop()
                except Exception as e:
                    logger.error("关闭会话 '%s' 失败: %s", sid, e)
        logger.info("所有 Vitis 会话已清理完毕。")

    def list_sessions(self) -> list[dict]:
        dead = [
            sid for sid, s in self._sessions.items()
            if not s.is_alive
        ]
        for sid in dead:
            del self._sessions[sid]
        return [s.status_dict() for s in self._sessions.values()]


# --------------------------------------------------------------------------- #
#  Lifespan & FastMCP
# --------------------------------------------------------------------------- #

@dataclass
class AppContext:
    session_manager: SessionManager


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    global _manager_ref

    try:
        vitis_path = find_vitis()
        logger.info("检测到 Vitis: %s", vitis_path)
    except FileNotFoundError as e:
        logger.warning("Vitis 路径检测失败: %s", e)
        logger.warning("工具仍可使用，但需要在 start_session 时手动指定路径。")
        vitis_path = ""

    manager = SessionManager(vitis_path=vitis_path)
    _manager_ref = manager
    try:
        yield AppContext(session_manager=manager)
    finally:
        _manager_ref = None
        await manager.close_all()


mcp = FastMCP("vitis-mcp", lifespan=app_lifespan)


# --------------------------------------------------------------------------- #
#  辅助函数（所有工具共享）
# --------------------------------------------------------------------------- #

def _get_manager(ctx) -> SessionManager:
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return app_ctx.session_manager


_NO_SESSION = "[ERROR] 会话 '{sid}' 不存在。请先调用 start_session。"


def _require_session(ctx, session_id: str) -> VitisSession | None:
    return _get_manager(ctx).get(session_id)


async def _safe_execute(
    session: VitisSession,
    code: str,
    timeout: float,
    error_label: str,
) -> str:
    """安全执行 Python 命令，异常时返回错误字符串而非抛出。"""
    try:
        result = await session.execute(code, timeout=timeout)
        return result.summary
    except Exception as e:
        return f"[ERROR] {error_label}: {e}"


# --------------------------------------------------------------------------- #
#  MCP Resources
# --------------------------------------------------------------------------- #

@mcp.resource("vitis://sessions")
def resource_sessions() -> str:
    """所有 Vitis 会话的状态信息（JSON）。"""
    if _manager_ref is None:
        return json.dumps({"sessions": [], "message": "服务器未就绪"})
    sessions = _manager_ref.list_sessions()
    if not sessions:
        return json.dumps({"sessions": [], "message": "当前没有活跃会话"})
    return json.dumps({"sessions": sessions}, ensure_ascii=False)


# --------------------------------------------------------------------------- #
#  MCP Prompts
# --------------------------------------------------------------------------- #

@mcp.prompt()
def embedded_workflow() -> str:
    """嵌入式软件开发流程引导：从平台创建到应用编译。"""
    return (
        "请按以下 Vitis 嵌入式开发流程操作：\n\n"
        "1. **启动会话**: `start_session` 启动 Vitis Python REPL\n"
        "2. **创建平台**: `create_platform` 从 XSA 创建硬件平台\n"
        "3. **创建应用**: `create_app` 创建裸机/FreeRTOS 应用\n"
        "4. **导入源码**: `import_sources` 导入 C/C++ 文件\n"
        "5. **配置 BSP**: `set_bsp_config` 修改 BSP 参数\n"
        "6. **编译应用**: `build_app` 编译生成 ELF\n"
        "7. **下载调试**: `hw_connect` → `hw_program_fpga` → `hw_program_elf`\n\n"
        "每步完成后检查输出确认成功。如有错误用 `get_build_log` 查看详情。"
    )


@mcp.prompt()
def debug_workflow() -> str:
    """硬件调试流程引导：JTAG 连接到程序下载。"""
    return (
        "硬件调试流程：\n\n"
        "1. **连接硬件**: `hw_connect` 连接 JTAG / hw_server\n"
        "2. **查看目标**: `hw_list_targets` 列出所有处理器和 PL\n"
        "3. **下载比特流**: `hw_program_fpga` 配置 FPGA\n"
        "4. **下载 ELF**: `hw_program_elf` 烧录应用程序\n"
        "5. **调试控制**: `hw_stop` / `hw_continue` / `hw_step`\n"
        "6. **查看状态**: `hw_read_register` / `hw_read_memory` / `hw_backtrace`\n"
        "7. **断开连接**: `hw_disconnect`"
    )


# --------------------------------------------------------------------------- #
#  导入工具模块（触发 @mcp.tool() 注册）
# --------------------------------------------------------------------------- #

import vitis_mcp.tools.session_tools  # noqa: E402, F401
import vitis_mcp.tools.platform_tools  # noqa: E402, F401
import vitis_mcp.tools.app_tools  # noqa: E402, F401
import vitis_mcp.tools.bsp_tools  # noqa: E402, F401
import vitis_mcp.tools.workspace_tools  # noqa: E402, F401
import vitis_mcp.tools.xsdb_tools  # noqa: E402, F401
