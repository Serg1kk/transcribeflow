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
