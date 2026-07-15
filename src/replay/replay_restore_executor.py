from __future__ import annotations

import argparse
import ctypes
import fcntl
import hashlib
import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


AT_FDCWD = -2
RENAME_SWAP = 0x00000002
TARGET_FILES = ("replay_inputs.csv", "replay_performance_series.csv")
CONFIRMED_DAMAGED_HASHES = {
    "replay_inputs.csv": "e3e4096df09232333622931dfcc28255a78cd67fad2b9bae2027263028f2d6dd",
    "replay_performance_series.csv": "eb326fa461b54e54f5539e8605c014cd96d2aa35b96e409ee122cdd83cfcb731",
}


class ReplayRestoreError(RuntimeError):
    """Raised when restore execution cannot complete safely."""


@dataclass(frozen=True)
class RestoreExecutionResult:
    current_root: str
    stage_root: str
    lock_path: str
    target_hashes_before: dict[str, str]
    target_hashes_after: dict[str, str]
    rollback_snapshot_hashes: dict[str, str]
    unrelated_hashes_before: dict[str, str]
    unrelated_hashes_after: dict[str, str]


def restore_replay_current_from_candidate(
    *,
    repo_root: str | Path,
    candidate_root: str | Path,
    expected_candidate_hashes: dict[str, str],
    target_files: Iterable[str] = TARGET_FILES,
    allow_stale_recovery: bool = False,
    stale_recovery_reason: str = "guarded stale stage recovery",
) -> RestoreExecutionResult:
    repo_root_path = Path(repo_root).resolve()
    candidate_root_path = Path(candidate_root).resolve()
    current_root = (repo_root_path / "data" / "current").resolve()
    stage_root = current_root.with_name(current_root.name + ".__restore_stage__")
    lock_path = current_root.with_name(current_root.name + ".__restore_lock__")

    targets = tuple(target_files)
    if stage_root.exists():
        if not allow_stale_recovery:
            raise ReplayRestoreError(f"Staging directory already exists: {stage_root}")
        _recover_stale_stage_and_lock(
            current_root=current_root,
            stage_root=stage_root,
            lock_path=lock_path,
            candidate_root=candidate_root_path,
            targets=targets,
            reason=stale_recovery_reason,
        )

    _require_swap_support()

    target_hashes_before = {name: _sha256(current_root / name) for name in targets}
    unrelated_hashes_before = _hash_tree(current_root, exclude_names=set(targets))

    candidate_hashes = {name: _sha256(candidate_root_path / name) for name in targets}
    if candidate_hashes != expected_candidate_hashes:
        raise ReplayRestoreError(
            f"Candidate hashes do not match approved values: got={candidate_hashes} expected={expected_candidate_hashes}"
        )

    with _locked(lock_path):
        _hardlink_tree(current_root, stage_root)
        try:
            for name in targets:
                stage_file = stage_root / name
                if stage_file.exists():
                    stage_file.unlink()
                shutil.copy2(candidate_root_path / name, stage_file)
                _fsync_file(stage_file)
            _fsync_dir(stage_root)

            _rename_swap(stage_root, current_root)

            target_hashes_after = {name: _sha256(current_root / name) for name in targets}
            unrelated_hashes_after = _hash_tree(current_root, exclude_names=set(targets))
            rollback_snapshot_hashes = {name: _sha256(stage_root / name) for name in targets}

            if target_hashes_after != expected_candidate_hashes:
                _rename_swap(stage_root, current_root)
                raise ReplayRestoreError(
                    f"Published hashes do not match candidate: {target_hashes_after}"
                )
            if unrelated_hashes_after != unrelated_hashes_before:
                _rename_swap(stage_root, current_root)
                raise ReplayRestoreError("Unrelated current artifacts changed during restore.")

            return RestoreExecutionResult(
                current_root=str(current_root),
                stage_root=str(stage_root),
                lock_path=str(lock_path),
                target_hashes_before=target_hashes_before,
                target_hashes_after=target_hashes_after,
                rollback_snapshot_hashes=rollback_snapshot_hashes,
                unrelated_hashes_before=unrelated_hashes_before,
                unrelated_hashes_after=unrelated_hashes_after,
            )
        except Exception:
            if stage_root.exists() and not current_root.exists():
                _rename_swap(stage_root, current_root)
            elif stage_root.exists() and current_root.exists():
                # if swap did not happen yet, just clean the staged hard-link tree
                shutil.rmtree(stage_root, ignore_errors=True)
            raise


@contextmanager
def _locked(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _require_swap_support() -> None:
    libc = _libc()
    if not hasattr(libc, "renameatx_np"):
        raise ReplayRestoreError("renameatx_np RENAME_SWAP is unavailable on this platform.")


def _libc():
    return ctypes.CDLL("/usr/lib/libc.dylib", use_errno=True)


def _rename_swap(path_a: Path, path_b: Path) -> None:
    libc = _libc()
    renameatx_np = libc.renameatx_np
    renameatx_np.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameatx_np.restype = ctypes.c_int
    rc = renameatx_np(
        AT_FDCWD,
        os.fsencode(str(path_a)),
        AT_FDCWD,
        os.fsencode(str(path_b)),
        RENAME_SWAP,
    )
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), f"renameatx_np({path_a}, {path_b})")


def _hardlink_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=False)
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        dst_dir = dst / rel
        dst_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (dst_dir / d).mkdir(exist_ok=True)
        for f in files:
            os.link(Path(root) / f, dst_dir / f)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _hash_tree(root: Path, *, exclude_names: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if path.name in exclude_names:
            continue
        out[rel] = _sha256(path)
    return out


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _recover_stale_stage_and_lock(
    *,
    current_root: Path,
    stage_root: Path,
    lock_path: Path,
    candidate_root: Path,
    targets: tuple[str, ...],
    reason: str,
) -> None:
    if not stage_root.exists():
        raise ReplayRestoreError("Stale recovery requires an existing stage directory.")
    if not _target_set_supported(targets):
        raise ReplayRestoreError("Stale recovery supports only the default replay target file set.")
    if _lock_has_active_holder(lock_path):
        raise ReplayRestoreError(f"Cannot recover stale stage while lock appears active: {lock_path}")

    current_hashes = {name: _sha256(current_root / name) for name in targets}
    stage_hashes = {name: _sha256(stage_root / name) for name in targets}

    if stage_hashes != current_hashes:
        raise ReplayRestoreError(
            f"Cannot recover stale stage because stage/current target hashes differ: "
            f"stage={stage_hashes} current={current_hashes}"
        )
    if current_hashes != CONFIRMED_DAMAGED_HASHES:
        raise ReplayRestoreError(
            "Cannot recover stale stage because target hashes are not the confirmed damaged pair. "
            f"got={current_hashes} expected={CONFIRMED_DAMAGED_HASHES}"
        )

    _record_stale_recovery(
        candidate_root=candidate_root,
        current_root=current_root,
        stage_root=stage_root,
        lock_path=lock_path,
        current_hashes=current_hashes,
        stage_hashes=stage_hashes,
        reason=reason,
    )

    shutil.rmtree(stage_root)
    if lock_path.exists():
        lock_path.unlink()


def _target_set_supported(targets: tuple[str, ...]) -> bool:
    return tuple(sorted(targets)) == tuple(sorted(TARGET_FILES))


def _lock_has_active_holder(lock_path: Path) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return False


def _record_stale_recovery(
    *,
    candidate_root: Path,
    current_root: Path,
    stage_root: Path,
    lock_path: Path,
    current_hashes: dict[str, str],
    stage_hashes: dict[str, str],
    reason: str,
) -> None:
    package_root = _infer_restore_package_root(candidate_root)
    backup_root = package_root / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    report_path = backup_root / "stale_recovery_record.json"

    entry = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "reason": reason,
        "current_root": str(current_root),
        "stage_path": str(stage_root),
        "lock_path": str(lock_path),
        "stage_exists": stage_root.exists(),
        "lock_exists": lock_path.exists(),
        "stage_mtime_utc": _stat_mtime_utc(stage_root),
        "lock_mtime_utc": _stat_mtime_utc(lock_path),
        "current_target_hashes": current_hashes,
        "stage_target_hashes": stage_hashes,
        "confirmed_damaged_hashes": CONFIRMED_DAMAGED_HASHES,
    }

    payload = {"entries": [entry]}
    if report_path.exists():
        try:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("entries"), list):
                payload = existing
                payload["entries"].append(entry)
        except Exception:
            payload = {"entries": [entry]}
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _infer_restore_package_root(candidate_root: Path) -> Path:
    if candidate_root.name == "candidate":
        return candidate_root.parent
    return candidate_root


def _stat_mtime_utc(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _main() -> int:
    parser = argparse.ArgumentParser(description="Execute controlled replay current restore from approved candidate.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--expected-replay-inputs-sha256", required=True)
    parser.add_argument("--expected-replay-series-sha256", required=True)
    parser.add_argument("--allow-stale-recovery", action="store_true")
    args = parser.parse_args()

    result = restore_replay_current_from_candidate(
        repo_root=args.repo_root,
        candidate_root=args.candidate_root,
        expected_candidate_hashes={
            "replay_inputs.csv": args.expected_replay_inputs_sha256,
            "replay_performance_series.csv": args.expected_replay_series_sha256,
        },
        allow_stale_recovery=args.allow_stale_recovery,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
