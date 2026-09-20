from __future__ import annotations

import threading
import time

_EPOCH_MS = 1_704_067_200_000  # 2024-01-01 UTC
_WORKER_ID = 1
_SEQ_MASK = 0xFFF
_lock = threading.Lock()
_last_ms = 0
_seq = 0


def new_id() -> str:
    """十进制雪花字符串，与契约 id=string 对齐。全站一份，避免各包各造 worker。"""
    global _last_ms, _seq
    with _lock:
        now = int(time.time() * 1000)
        if now == _last_ms:
            _seq = (_seq + 1) & _SEQ_MASK
            if _seq == 0:
                now += 1
        else:
            _seq = 0
        _last_ms = now
        value = ((now - _EPOCH_MS) << 22) | (_WORKER_ID << 12) | _seq
        return str(value)
