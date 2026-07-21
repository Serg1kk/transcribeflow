# tests/test_pyannote_compat.py
import pytest

from workers.pyannote_compat import hf_token_kwarg


def _v3_from_pretrained(checkpoint, hparams_file=None, use_auth_token=None, cache_dir=None):
    """Signature of pyannote.audio 3.x Pipeline.from_pretrained."""


def _v4_from_pretrained(checkpoint, revision=None, hparams_file=None, token=None, cache_dir=None):
    """Signature of pyannote.audio 4.x Pipeline.from_pretrained."""


def test_uses_token_on_pyannote_4():
    assert hf_token_kwarg(_v4_from_pretrained, "hf_abc") == {"token": "hf_abc"}


def test_uses_use_auth_token_on_pyannote_3():
    assert hf_token_kwarg(_v3_from_pretrained, "hf_abc") == {"use_auth_token": "hf_abc"}


@pytest.mark.parametrize("func", [_v3_from_pretrained, _v4_from_pretrained])
def test_no_token_passes_nothing(func):
    """Without a token, defer to ambient HF credentials rather than sending None."""
    assert hf_token_kwarg(func, None) == {}


def test_unknown_signature_passes_nothing():
    """Never guess a kwarg name the callable does not declare."""
    def no_auth_param(checkpoint):
        pass

    assert hf_token_kwarg(no_auth_param, "hf_abc") == {}


def test_matches_installed_pyannote():
    """The kwarg we build must actually be accepted by the installed pyannote.

    Guards the regression this helper exists for: the diarization call was
    switched to `use_auth_token`, which pyannote 4.x rejects with
    "unexpected keyword argument", failing every diarization run.
    """
    pyannote_audio = pytest.importorskip("pyannote.audio")

    import inspect

    kwargs = hf_token_kwarg(pyannote_audio.Pipeline.from_pretrained, "hf_abc")
    params = inspect.signature(pyannote_audio.Pipeline.from_pretrained).parameters
    assert kwargs, "installed pyannote should accept some auth kwarg"
    for name in kwargs:
        assert name in params


def test_falls_back_to_cache_when_hub_raises():
    """A hub failure must not fail the load when weights are already cached."""
    import huggingface_hub.constants as hf_constants

    calls = []

    def flaky_from_pretrained(checkpoint, token=None):
        offline = hf_constants.HF_HUB_OFFLINE
        calls.append(offline)
        if not offline:
            raise OSError("SSLEOFError: EOF occurred in violation of protocol")
        return "cached-pipeline"

    from workers.pyannote_compat import load_pretrained

    assert load_pretrained(flaky_from_pretrained, "pyannote/x", "hf_abc") == "cached-pipeline"
    assert calls == [False, True], "expected one online attempt then one cache-only retry"


def test_offline_flag_is_restored_after_fallback():
    """The forced-offline state must not leak into the rest of the process."""
    import os

    import huggingface_hub.constants as hf_constants

    before_flag = hf_constants.HF_HUB_OFFLINE
    before_env = os.environ.get("HF_HUB_OFFLINE")

    def flaky_from_pretrained(checkpoint, token=None):
        if not hf_constants.HF_HUB_OFFLINE:
            raise OSError("network down")
        return "cached-pipeline"

    from workers.pyannote_compat import load_pretrained

    load_pretrained(flaky_from_pretrained, "pyannote/x", None)

    assert hf_constants.HF_HUB_OFFLINE == before_flag
    assert os.environ.get("HF_HUB_OFFLINE") == before_env


def test_original_error_is_raised_when_cache_also_misses():
    """Don't mask a real problem behind a misleading cache-miss message."""
    def always_fails(checkpoint, token=None):
        if not __import__("huggingface_hub.constants", fromlist=["x"]).HF_HUB_OFFLINE:
            raise OSError("401 Unauthorized: gated repo")
        raise OSError("not found in local cache")

    from workers.pyannote_compat import load_pretrained

    with pytest.raises(OSError, match="gated repo"):
        load_pretrained(always_fails, "pyannote/x", "hf_abc")
