"""Vitis 路径自动检测。

优先级：
1. 显式参数
2. VITIS_PATH 环境变量
3. 系统 PATH 中的 vitis / vitis.bat
4. 默认安装目录扫描（最新版本优先）
"""

import glob
import logging
import os
import platform
import shutil

logger = logging.getLogger(__name__)


def find_vitis(vitis_path: str | None = None) -> str:
    """查找 Vitis 可执行文件路径。

    Args:
        vitis_path: 可选的显式路径。

    Returns:
        Vitis 可执行文件的完整路径。

    Raises:
        FileNotFoundError: 找不到 Vitis。
    """
    # 1. 显式参数
    if vitis_path:
        if os.path.isfile(vitis_path):
            return vitis_path
        raise FileNotFoundError(f"指定的 Vitis 路径不存在: {vitis_path}")

    # 2. 环境变量
    env_path = os.environ.get("VITIS_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 3. 系统 PATH
    is_win = platform.system() == "Windows"
    names = ["vitis.bat", "vitis"] if is_win else ["vitis"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found

    # 4. 默认安装目录扫描
    if is_win:
        patterns = [
            "C:/Xilinx/Vitis/*/bin/vitis.bat",
            "D:/Xilinx/Vitis/*/bin/vitis.bat",
        ]
    else:
        patterns = [
            "/opt/Xilinx/Vitis/*/bin/vitis",
            "/tools/Xilinx/Vitis/*/bin/vitis",
        ]

    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    if candidates:
        # 按版本号降序排列，选最新的
        candidates.sort(reverse=True)
        return candidates[0]

    raise FileNotFoundError(
        "未找到 Vitis。请设置 VITIS_PATH 环境变量，"
        "或在 start_session 时通过 vitis_path 参数指定路径。"
    )
