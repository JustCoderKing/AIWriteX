# -*- coding: UTF-8 -*-
"""给已安装的 aiforge-engine 正式加入 minimax 类型支持。

在虚拟环境中执行:
    python scripts/patch_aiforge_minimax.py
重装 aiforge-engine 后需要再执行一次。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _aiforge_root() -> Path:
    import aiforge

    return Path(aiforge.__file__).resolve().parent


def patch_llm_manager(root: Path) -> bool:
    path = root / "llm" / "llm_manager.py"
    text = path.read_text(encoding="utf-8")
    if '"minimax"' in text and "mistral\",\n            \"minimax\"" in text.replace("'", '"'):
        # already patched in common form
        pass

    pattern = (
        r'(if client_type in \[\s*"openai",\s*"deepseek",\s*"grok",\s*"gemini",\s*'
        r'"qwen",\s*"claude",\s*"cohere",\s*"mistral",)\s*(\])'
    )
    replacement = r'\1\n            "minimax",\2'
    new_text, count = re.subn(pattern, replacement, text, count=1)
    if count == 0:
        if '"minimax"' in text:
            print(f"[skip] already patched: {path}")
            return False
        raise RuntimeError(f"未能匹配 llm_manager.py 中的类型列表: {path}")

    path.write_text(new_text, encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def patch_adapter_factory(root: Path) -> bool:
    path = root / "llm" / "adapters" / "adapter_factory.py"
    text = path.read_text(encoding="utf-8")
    if '"minimax": OpenAIAdapter' in text:
        print(f"[skip] already patched: {path}")
        return False

    needle = '"deepseek": OpenAIAdapter,'
    if needle not in text:
        raise RuntimeError(f"未能匹配 adapter_factory.py: {path}")

    new_text = text.replace(
        needle,
        '"deepseek": OpenAIAdapter,\n        "minimax": OpenAIAdapter,',
        1,
    )
    path.write_text(new_text, encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def main() -> int:
    root = _aiforge_root()
    print(f"aiforge root: {root}")
    patch_llm_manager(root)
    patch_adapter_factory(root)
    print("MiniMax 类型已加入 aiforge 支持列表。配置中使用 type = \"minimax\" 即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
