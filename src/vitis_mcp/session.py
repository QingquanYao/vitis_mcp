"""VitisSession：Vitis Python REPL 子进程管理与哨兵通信协议。

管理一个持久的 `vitis -i` 交互式 Python 进程，
通过 base64 + sentinel 协议可靠地执行命令并收集输出。
"""

import asyncio
import logging
import time
from enum import Enum

from vitis_mcp.python_utils import (
    CommandResult,
    clean_output,
    generate_sentinel,
    make_sentinel_pattern,
    wrap_python_command,
)

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """会话状态枚举。"""
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


class VitisSession:
    """Vitis Python 交互式子进程会话。

    通过 asyncio subprocess 管理一个 `vitis -i` 进程，
    使用 base64 编码 + sentinel 协议实现可靠的命令执行与输出采集。
    """

    def __init__(self, vitis_path: str, session_id: str = "default"):
        self.vitis_path = vitis_path
        self.session_id = session_id
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._state = SessionState.STOPPED
        self._start_time: float | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_alive(self) -> bool:
        return (
            self._process is not None
            and self._process.returncode is None
        )

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    async def start(self, timeout: float = 120.0) -> str:
        """启动 Vitis Python REPL 子进程。

        Args:
            timeout: 等待 Vitis 启动完成的超时秒数。

        Returns:
            Vitis 启动横幅（版本信息等）。

        Raises:
            RuntimeError: 进程启动失败或超时。
        """
        if self.is_alive:
            return f"会话 '{self.session_id}' 已在运行中。"

        self._state = SessionState.STARTING
        logger.info("启动 Vitis 会话 '%s': %s", self.session_id, self.vitis_path)

        try:
            self._process = await asyncio.create_subprocess_exec(
                self.vitis_path,
                "-i",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (OSError, FileNotFoundError) as e:
            self._state = SessionState.ERROR
            raise RuntimeError(f"无法启动 Vitis: {e}") from e

        # 等待 REPL 就绪
        banner = await self._read_startup_banner(timeout)
        self._state = SessionState.READY
        self._start_time = time.time()
        logger.info("Vitis 会话 '%s' 启动成功", self.session_id)
        return banner

    async def _read_startup_banner(self, timeout: float) -> str:
        """读取 Vitis 启动时的初始输出并检测 REPL 就绪。

        发送一个探测命令 + sentinel 来检测 Vitis 何时完成初始化。
        """
        sentinel = generate_sentinel()
        pattern = make_sentinel_pattern(sentinel)

        # 发送探测命令
        probe = wrap_python_command('print("VMCP_READY")', sentinel)
        assert self._process and self._process.stdin and self._process.stdout
        self._process.stdin.write(probe.encode("utf-8"))
        await self._process.stdin.drain()

        lines: list[str] = []
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError()

                raw = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=remaining,
                )
                if not raw:
                    # EOF — 进程意外退出
                    stderr_out = ""
                    if self._process.stderr:
                        try:
                            stderr_out = (await asyncio.wait_for(
                                self._process.stderr.read(), timeout=2.0
                            )).decode("utf-8", errors="replace")
                        except asyncio.TimeoutError:
                            pass
                    raise RuntimeError(
                        f"Vitis 进程意外退出。stderr: {stderr_out}"
                    )

                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                m = pattern.search(line)
                if m:
                    break
                lines.append(line)

        except asyncio.TimeoutError:
            self._state = SessionState.ERROR
            raise RuntimeError(
                f"Vitis 启动超时（{timeout}s）。"
                "请检查 Vitis 路径是否正确，或尝试增大超时值。"
            )

        return clean_output("\n".join(lines))

    async def execute(
        self,
        python_code: str,
        timeout: float = 120.0,
    ) -> CommandResult:
        """执行一段 Python 代码并返回结果。

        通过 asyncio.Lock 确保同一时刻只有一条命令在执行。

        Args:
            python_code: Python 代码文本（可多行）。
            timeout: 命令执行超时秒数。

        Returns:
            CommandResult 包含输出文本、返回码和错误标志。

        Raises:
            RuntimeError: 会话未启动或已停止。
            asyncio.TimeoutError: 命令执行超时。
        """
        if not self.is_alive:
            raise RuntimeError(
                f"会话 '{self.session_id}' 未运行。请先调用 start_session。"
            )

        async with self._lock:
            self._state = SessionState.BUSY
            try:
                result = await self._execute_impl(python_code, timeout)
                self._state = SessionState.READY
                return result
            except Exception:
                if self.is_alive:
                    self._state = SessionState.READY
                else:
                    self._state = SessionState.ERROR
                raise

    async def _execute_impl(
        self,
        python_code: str,
        timeout: float,
    ) -> CommandResult:
        """内部执行实现（不加锁）。"""
        assert self._process and self._process.stdin and self._process.stdout

        sentinel = generate_sentinel()
        pattern = make_sentinel_pattern(sentinel)
        wrapped = wrap_python_command(python_code, sentinel)

        logger.debug(
            "[%s] 发送命令: %s", self.session_id, python_code[:200]
        )
        self._process.stdin.write(wrapped.encode("utf-8"))
        await self._process.stdin.drain()

        # 收集输出直到匹配 sentinel
        output_lines: list[str] = []
        return_code = -1

        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError()

                raw = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=remaining,
                )
                if not raw:
                    raise RuntimeError(
                        f"Vitis 进程意外终止（会话 '{self.session_id}'）。"
                    )

                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")

                m = pattern.search(line)
                if m:
                    return_code = int(m.group(1))
                    break

                output_lines.append(line)

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"命令执行超时（{timeout}s）。\n"
                f"会话: {self.session_id}\n"
                f"命令: {python_code[:200]}"
            )

        output = clean_output("\n".join(output_lines))
        is_error = return_code != 0

        logger.debug(
            "[%s] 结果: rc=%d, output=%d chars",
            self.session_id, return_code, len(output),
        )

        return CommandResult(
            output=output,
            return_code=return_code,
            is_error=is_error,
        )

    async def stop(self, timeout: float = 10.0) -> None:
        """优雅地关闭 Vitis 会话。"""
        if not self._process:
            return

        logger.info("正在关闭 Vitis 会话 '%s'...", self.session_id)

        if self.is_alive and self._process.stdin:
            try:
                self._process.stdin.write(b"exit()\n")
                await self._process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        if self.is_alive:
            try:
                await asyncio.wait_for(
                    self._process.wait(), timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Vitis 会话 '%s' 未在 %ss 内退出，强制终止。",
                    self.session_id, timeout,
                )
                self._process.kill()
                await self._process.wait()

        self._state = SessionState.STOPPED
        self._process = None
        logger.info("Vitis 会话 '%s' 已关闭。", self.session_id)

    def status_dict(self) -> dict:
        """返回会话状态信息字典。"""
        return {
            "session_id": self.session_id,
            "state": self._state.value,
            "vitis_path": self.vitis_path,
            "is_alive": self.is_alive,
            "uptime_seconds": round(self.uptime_seconds, 1),
        }
