from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from src.replay import replay_restore_executor
from src.replay.replay_restore_executor import ReplayRestoreError, restore_replay_current_from_candidate


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _make_default_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    current = repo / "data" / "current"
    candidate = repo / "candidate"

    _write(current / "replay_inputs.csv", "replay_id\nOLD\n")
    _write(
        current / "replay_performance_series.csv",
        "series_id,replay_id,series_type,date,value,cumulative_return,source,coverage_status\n"
        "S,OLD,TOP_N_STRATEGY,2026-01-01,1,0,src,AVAILABLE\n",
    )
    _write(current / "security_prices.csv", "symbol,price\nAAA,1\n")

    _write(candidate / "replay_inputs.csv", "replay_id\nNEW\n")
    _write(
        candidate / "replay_performance_series.csv",
        "series_id,replay_id,series_type,date,value,cumulative_return,source,coverage_status\n"
        "S,NEW,TOP_N_STRATEGY,2026-05-14,2,0,src,AVAILABLE\n",
    )
    return repo, current, candidate


def _expected_candidate(candidate: Path) -> dict[str, str]:
    return {
        "replay_inputs.csv": _sha(candidate / "replay_inputs.csv"),
        "replay_performance_series.csv": _sha(candidate / "replay_performance_series.csv"),
    }


def test_restore_replay_current_from_candidate_swaps_pair_and_preserves_unrelated_files(tmp_path: Path) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    expected = _expected_candidate(candidate)
    unrelated_before = _sha(current / "security_prices.csv")
    old_inputs = _sha(current / "replay_inputs.csv")
    old_series = _sha(current / "replay_performance_series.csv")

    result = restore_replay_current_from_candidate(
        repo_root=repo,
        candidate_root=candidate,
        expected_candidate_hashes=expected,
    )

    assert _sha(current / "replay_inputs.csv") == expected["replay_inputs.csv"]
    assert _sha(current / "replay_performance_series.csv") == expected["replay_performance_series.csv"]
    assert _sha(current / "security_prices.csv") == unrelated_before

    rollback_dir = Path(result.stage_root)
    assert _sha(rollback_dir / "replay_inputs.csv") == old_inputs
    assert _sha(rollback_dir / "replay_performance_series.csv") == old_series
    assert _sha(rollback_dir / "security_prices.csv") == unrelated_before


def test_restore_replay_current_from_candidate_rejects_unapproved_hashes(tmp_path: Path) -> None:
    repo, _current, candidate = _make_default_repo(tmp_path)

    bad = {
        "replay_inputs.csv": "x",
        "replay_performance_series.csv": "y",
    }

    try:
        restore_replay_current_from_candidate(
            repo_root=repo,
            candidate_root=candidate,
            expected_candidate_hashes=bad,
        )
    except Exception as exc:
        assert "Candidate hashes do not match approved values" in str(exc)
    else:
        raise AssertionError("expected restore to reject mismatched candidate hashes")


def test_default_behavior_rejects_existing_stage(tmp_path: Path) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    stage = current.with_name(current.name + ".__restore_stage__")
    stage.mkdir(parents=True)

    with pytest.raises(ReplayRestoreError, match="Staging directory already exists"):
        restore_replay_current_from_candidate(
            repo_root=repo,
            candidate_root=candidate,
            expected_candidate_hashes=_expected_candidate(candidate),
        )


def test_explicit_recovery_rejects_active_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    stage = current.with_name(current.name + ".__restore_stage__")
    stage.mkdir(parents=True)
    _write(stage / "replay_inputs.csv", (current / "replay_inputs.csv").read_text(encoding="utf-8"))
    _write(
        stage / "replay_performance_series.csv",
        (current / "replay_performance_series.csv").read_text(encoding="utf-8"),
    )

    damaged = {
        "replay_inputs.csv": _sha(current / "replay_inputs.csv"),
        "replay_performance_series.csv": _sha(current / "replay_performance_series.csv"),
    }
    monkeypatch.setattr(replay_restore_executor, "CONFIRMED_DAMAGED_HASHES", damaged)
    monkeypatch.setattr(replay_restore_executor, "_lock_has_active_holder", lambda _path: True)

    with pytest.raises(ReplayRestoreError, match="lock appears active"):
        restore_replay_current_from_candidate(
            repo_root=repo,
            candidate_root=candidate,
            expected_candidate_hashes=_expected_candidate(candidate),
            allow_stale_recovery=True,
        )


def test_explicit_recovery_rejects_stage_current_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    stage = current.with_name(current.name + ".__restore_stage__")
    stage.mkdir(parents=True)
    _write(stage / "replay_inputs.csv", "replay_id\nDIFF\n")
    _write(
        stage / "replay_performance_series.csv",
        "series_id,replay_id,series_type,date,value,cumulative_return,source,coverage_status\n"
        "S,DIFF,TOP_N_STRATEGY,2026-01-01,9,0,src,AVAILABLE\n",
    )

    damaged = {
        "replay_inputs.csv": _sha(current / "replay_inputs.csv"),
        "replay_performance_series.csv": _sha(current / "replay_performance_series.csv"),
    }
    monkeypatch.setattr(replay_restore_executor, "CONFIRMED_DAMAGED_HASHES", damaged)

    with pytest.raises(ReplayRestoreError, match="stage/current target hashes differ"):
        restore_replay_current_from_candidate(
            repo_root=repo,
            candidate_root=candidate,
            expected_candidate_hashes=_expected_candidate(candidate),
            allow_stale_recovery=True,
        )


def test_explicit_recovery_accepts_inactive_lock_identical_damaged_pair_and_preserves_unrelated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    stage = current.with_name(current.name + ".__restore_stage__")
    lock = current.with_name(current.name + ".__restore_lock__")
    stage.mkdir(parents=True)
    _write(lock, "")

    _write(stage / "replay_inputs.csv", (current / "replay_inputs.csv").read_text(encoding="utf-8"))
    _write(
        stage / "replay_performance_series.csv",
        (current / "replay_performance_series.csv").read_text(encoding="utf-8"),
    )
    _write(stage / "security_prices.csv", (current / "security_prices.csv").read_text(encoding="utf-8"))
    _write(repo / "keep_me.txt", "do-not-touch")

    damaged = {
        "replay_inputs.csv": _sha(current / "replay_inputs.csv"),
        "replay_performance_series.csv": _sha(current / "replay_performance_series.csv"),
    }
    monkeypatch.setattr(replay_restore_executor, "CONFIRMED_DAMAGED_HASHES", damaged)

    restore_replay_current_from_candidate(
        repo_root=repo,
        candidate_root=candidate,
        expected_candidate_hashes=_expected_candidate(candidate),
        allow_stale_recovery=True,
    )

    assert (repo / "keep_me.txt").read_text(encoding="utf-8") == "do-not-touch"
    assert _sha(current / "replay_inputs.csv") == _sha(candidate / "replay_inputs.csv")
    assert _sha(current / "replay_performance_series.csv") == _sha(candidate / "replay_performance_series.csv")


def test_candidate_publication_produces_expected_hashes(tmp_path: Path) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    expected = _expected_candidate(candidate)

    restore_replay_current_from_candidate(
        repo_root=repo,
        candidate_root=candidate,
        expected_candidate_hashes=expected,
    )

    assert _sha(current / "replay_inputs.csv") == expected["replay_inputs.csv"]
    assert _sha(current / "replay_performance_series.csv") == expected["replay_performance_series.csv"]


def test_post_publication_verification_fails_closed_and_rolls_back_on_mismatch(tmp_path: Path) -> None:
    repo, current, candidate = _make_default_repo(tmp_path)
    expected = _expected_candidate(candidate)
    old_inputs_hash = _sha(current / "replay_inputs.csv")
    old_series_hash = _sha(current / "replay_performance_series.csv")

    real_sha = replay_restore_executor._sha256

    def flaky_sha(path: Path) -> str:
        # Force post-swap verification mismatch only for current replay_inputs after publication.
        if path == current / "replay_inputs.csv" and "NEW" in path.read_text(encoding="utf-8"):
            return "00" * 32
        return real_sha(path)

    with patch("src.replay.replay_restore_executor._sha256", side_effect=flaky_sha):
        with pytest.raises(ReplayRestoreError, match="Published hashes do not match candidate"):
            restore_replay_current_from_candidate(
                repo_root=repo,
                candidate_root=candidate,
                expected_candidate_hashes=expected,
            )

    assert _sha(current / "replay_inputs.csv") == old_inputs_hash
    assert _sha(current / "replay_performance_series.csv") == old_series_hash
