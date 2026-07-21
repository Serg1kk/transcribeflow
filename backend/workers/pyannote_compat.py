# workers/pyannote_compat.py
"""Compatibility helpers for differing pyannote.audio versions."""
import contextlib
import inspect
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


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


@contextlib.contextmanager
def _hf_offline():
    """Force huggingface_hub to serve from its local cache only.

    The env var alone is not enough: huggingface_hub snapshots it into
    constants.HF_HUB_OFFLINE at import time, long before this runs. Both are
    set, and both are restored afterwards so the rest of the process keeps its
    normal online behaviour.
    """
    import huggingface_hub.constants as hf_constants

    previous_flag = hf_constants.HF_HUB_OFFLINE
    previous_env = os.environ.get("HF_HUB_OFFLINE")

    hf_constants.HF_HUB_OFFLINE = True
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        yield
    finally:
        hf_constants.HF_HUB_OFFLINE = previous_flag
        if previous_env is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous_env


def load_pretrained(from_pretrained: Callable, checkpoint: str, token: Optional[str]) -> Any:
    """Load a pyannote checkpoint, falling back to the local cache when offline.

    Hugging Face being unreachable — blocked, throttled, or simply down — would
    otherwise fail the whole transcription even though the weights are already
    cached, since pyannote contacts the hub on every load to check for updates.

    A cache-only retry is attempted on any failure. If that also fails the
    original error is raised, so genuine problems (bad token, gated repo, model
    never downloaded) still surface with their real message instead of a
    misleading "not found in cache".
    """
    kwargs = hf_token_kwarg(from_pretrained, token)

    try:
        return from_pretrained(checkpoint, **kwargs)
    except Exception as online_error:
        logger.warning(
            f"Could not load {checkpoint} from Hugging Face ({online_error}); "
            f"retrying from the local cache"
        )
        try:
            with _hf_offline():
                pipeline = from_pretrained(checkpoint, **kwargs)
        except Exception:
            raise online_error

        logger.info(f"Loaded {checkpoint} from the local cache (offline)")
        return pipeline
