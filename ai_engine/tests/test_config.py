import numpy as np
import pytest
from pydantic import ValidationError

from fraud_ai.config import EngineSettings
from fraud_ai.utils.privacy import PrivacyBoundaryError, assert_only_parameters, assert_path_within


def test_coordinator_has_no_bank_identity():
    s = EngineSettings(_env_file=None)
    assert not s.is_client
    with pytest.raises(RuntimeError):
        s.require_client()


def test_client_identity_validated():
    assert EngineSettings(bank_id="alpha", _env_file=None).require_client() == "alpha"
    with pytest.raises(ValidationError):
        EngineSettings(bank_id="delta", _env_file=None)


def test_invalid_fl_parameters_rejected():
    with pytest.raises(ValidationError):
        EngineSettings(fl_num_rounds=0, _env_file=None)


def test_path_guard_blocks_escape(tmp_path):
    own, other = tmp_path / "alpha", tmp_path / "beta"
    own.mkdir(); other.mkdir()
    assert assert_path_within(own / "tx.csv", own) == (own / "tx.csv").resolve()
    with pytest.raises(PrivacyBoundaryError):
        assert_path_within(own / ".." / "beta" / "tx.csv", own)
    link = own / "sneaky"
    try:
        link.symlink_to(other, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symbolic-link privilege is unavailable")
        raise
    with pytest.raises(PrivacyBoundaryError):
        assert_path_within(link / "tx.csv", own)


def test_only_parameter_arrays_may_leave_bank():
    assert_only_parameters([np.zeros(3), np.ones((2, 2))])
    for bad in ([{"amount": 10}], "records", [np.zeros(2), [1, 2]]):
        with pytest.raises(PrivacyBoundaryError):
            assert_only_parameters(bad)
