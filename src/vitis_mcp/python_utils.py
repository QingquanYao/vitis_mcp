"""Python sentinel 协议：命令包装、输出清洗、安全引用。

核心职责：
- 生成带 base64 编码 + try/except + sentinel 的包装命令
- 清洗 Vitis Python REPL 输出（去除提示符、ANSI 序列等）
- 安全引用工具（repr 引用、标识符验证、路径转换）
"""

import base64
import re
import uuid
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
#  常量 & 正则
# --------------------------------------------------------------------------- #

# Python REPL 提示符
_PYTHON_PROMPT_RE = re.compile(r"^(>>>|\.\.\.) ", re.MULTILINE)
# ANSI 转义序列
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
# 安全标识符白名单
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_.:\-]+$")
# 十六进制地址
_HEX_ADDR_RE = re.compile(r"^0[xX][0-9a-fA-F]+$")
# 纯数字
_DECIMAL_RE = re.compile(r"^\d+$")

# 输出截断阈值
MAX_OUTPUT_CHARS = 50_000


# --------------------------------------------------------------------------- #
#  CommandResult
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CommandResult:
    """Python 命令执行结果。"""
    output: str
    return_code: int
    is_error: bool

    @property
    def summary(self) -> str:
        """生成适合 MCP 返回的摘要，超长自动截断。"""
        text = self.output
        if len(text) > MAX_OUTPUT_CHARS:
            text = (
                text[:MAX_OUTPUT_CHARS]
                + f"\n\n... [输出已截断，共 {len(self.output)} 字符，"
                f"显示前 {MAX_OUTPUT_CHARS} 字符] ..."
            )
        if self.is_error:
            return f"[ERROR] (rc={self.return_code})\n{text}"
        return text if text.strip() else "[OK] 命令执行成功（无输出）"


# --------------------------------------------------------------------------- #
#  安全引用 & 验证
# --------------------------------------------------------------------------- #

def validate_identifier(value: str, param_name: str) -> str:
    """白名单验证标识符（平台名、应用名等）。

    仅允许字母、数字、下划线、点、冒号、连字符。
    """
    if not value or not _SAFE_ID_RE.match(value):
        raise ValueError(
            f"参数 '{param_name}' 含非法字符: {value!r}。"
            f"仅允许字母、数字、下划线、点、冒号、连字符。"
        )
    return value


def validate_address(value: str, param_name: str) -> str:
    """验证内存地址格式（十六进制或十进制）。"""
    if not (_HEX_ADDR_RE.match(value) or _DECIMAL_RE.match(value)):
        raise ValueError(
            f"参数 '{param_name}' 格式非法: {value!r}。"
            f"应为十六进制（如 0xFF000000）或十进制数字。"
        )
    return value


def safe_repr(value: str) -> str:
    """安全引用字符串，用于嵌入 Python 代码模板。

    使用 repr() 确保所有特殊字符被正确转义。
    """
    return repr(value)


def to_posix_path(path: str) -> str:
    """将 Windows 路径转为正斜杠格式。"""
    return path.replace("\\", "/")


# --------------------------------------------------------------------------- #
#  Sentinel 协议
# --------------------------------------------------------------------------- #

def generate_sentinel() -> str:
    """生成唯一的哨兵标记。"""
    return f"VMCP_{uuid.uuid4().hex[:12]}"


def wrap_python_command(user_code: str, sentinel: str) -> str:
    """将用户 Python 代码包装为带 sentinel 的安全执行脚本。

    安全机制：
    - Base64 编码用户代码，避免引号/缩进/特殊字符问题
    - try/except 捕获异常并打印 traceback
    - 打印唯一 sentinel 标记（含返回码）供 session 检测完成

    Args:
        user_code: 原始 Python 代码（可多行）。
        sentinel: 唯一哨兵标记字符串。

    Returns:
        包装后的 Python 代码（可直接发送到 REPL）。
    """
    encoded = base64.b64encode(user_code.encode("utf-8")).decode("ascii")
    # 单行 exec 版本，避免 REPL 中多行缩进问题
    return (
        f"exec("
        f"'import base64 as __b64, traceback as __tb, sys as __sys\\n'"
        f"'try:\\n'"
        f"'    __code = __b64.b64decode(\\'{encoded}\\').decode(\"utf-8\")\\n'"
        f"'    exec(__code)\\n'"
        f"'    print(\"<<<{sentinel}_RC=0>>>\")\\n'"
        f"'except Exception:\\n'"
        f"'    __tb.print_exc()\\n'"
        f"'    print(\"<<<{sentinel}_RC=1>>>\")\\n'"
        f"'__sys.stdout.flush()\\n'"
        f")\n"
    )


def make_sentinel_pattern(sentinel: str) -> re.Pattern:
    """生成匹配哨兵行的正则模式。"""
    return re.compile(rf"<<<{re.escape(sentinel)}_RC=(\d+)>>>")


# --------------------------------------------------------------------------- #
#  输出清洗
# --------------------------------------------------------------------------- #

def clean_output(raw: str) -> str:
    """清洗 Vitis Python REPL 输出。

    去除：
    - ANSI 转义序列
    - Python 提示符 (>>> / ...)
    - exec() 包装代码的回显行
    - 多余空行（3+ 合并为 2）
    - 首尾空白
    """
    text = _ANSI_ESCAPE_RE.sub("", raw)
    text = _PYTHON_PROMPT_RE.sub("", text)
    # 去除 sentinel 协议包装代码的回显
    text = re.sub(r"^exec\(.*\)$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^import base64 as __b64.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
