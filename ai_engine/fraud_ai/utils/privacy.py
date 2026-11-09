"""Guards that enforce the federated privacy boundary in code (not just in docker volumes)."""
from pathlib import Path


class PrivacyBoundaryError(RuntimeError):
    pass


def assert_path_within(path: Path, allowed_root: Path) -> Path:
    """Resolve `path` and ensure it lies inside `allowed_root` (blocks ../ and symlink escapes).

    A bank client uses this so it can only ever read from its own data directory.
    """
    resolved, root = Path(path).resolve(), Path(allowed_root).resolve()
    if resolved != root and root not in resolved.parents:
        raise PrivacyBoundaryError(f"{resolved} is outside the permitted directory {root}")
    return resolved


def assert_only_parameters(payload: object) -> None:
    """Coordinator-bound payloads must be model parameters (numpy arrays), never records."""
    import numpy as np

    if not isinstance(payload, (list, tuple)) or not all(isinstance(a, np.ndarray) for a in payload):
        raise PrivacyBoundaryError("only lists of numpy parameter arrays may leave a bank")
