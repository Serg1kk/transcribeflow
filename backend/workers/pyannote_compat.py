# workers/pyannote_compat.py
"""Compatibility helpers for differing pyannote.audio versions."""
import inspect
from typing import Any, Callable, Dict, Optional


def hf_token_kwarg(func: Callable, token: Optional[str]) -> Dict[str, Any]:
    """Build the Hugging Face auth kwarg accepted by `func`.

    pyannote.audio renamed `use_auth_token` to `token` in 4.0, so passing the
    wrong one raises TypeError: unexpected keyword argument. requirements.txt
    allows both majors (>=3.3.0), so pick the name the installed version
    actually declares instead of guessing.

    Returns an empty dict when no token is set, letting pyannote fall back to
    the ambient HF credentials (cached login or HF_TOKEN env var).
    """
    if token is None:
        return {}

    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        # Unintrospectable callable — assume the modern name.
        return {"token": token}

    if "token" in params:
        return {"token": token}
    if "use_auth_token" in params:
        return {"use_auth_token": token}

    # Neither name present: pass nothing rather than crash on an unknown kwarg.
    return {}
