"""
File-edit transactions for Chahlie.

Snapshots file contents before a batch of writes/edits. If the batch succeeds,
the snapshot is discarded; if it fails (or the user rolls back), every touched
file is restored to its pre-batch state.

Non-intrusive: files not present in the snapshot are not affected by rollback.
Files that didn't exist before the batch are deleted on rollback.

Intended usage
--------------
    tx = Transaction()
    tx.snapshot("foo.py")
    write_file("foo.py", new_content)
    tx.snapshot("bar.py")
    edit_file("bar.py", old, new)
    # if all good:
    tx.commit()
    # else:
    tx.rollback()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class _Snapshot:
    path: str
    existed: bool
    content: Optional[bytes]


@dataclass
class Transaction:
    """Lightweight file-state snapshot + restore."""
    snapshots: Dict[str, _Snapshot] = field(default_factory=dict)
    committed: bool = False

    def snapshot(self, path: str) -> None:
        """Record current state of `path` so it can be restored on rollback.

        Idempotent - snapshotting the same path twice is a no-op; we always
        keep the EARLIEST recorded state.
        """
        key = str(Path(path).resolve())
        if key in self.snapshots:
            return
        p = Path(path)
        if p.exists():
            try:
                data = p.read_bytes()
            except Exception:
                data = None
            self.snapshots[key] = _Snapshot(path=str(p), existed=True, content=data)
        else:
            self.snapshots[key] = _Snapshot(path=str(p), existed=False, content=None)

    def commit(self) -> None:
        """Mark transaction as complete. Snapshots can be dropped."""
        self.committed = True
        self.snapshots.clear()

    def rollback(self) -> Dict[str, str]:
        """Restore every snapshotted path.

        Returns a dict of {path: result_str} describing what happened to each.
        """
        if self.committed:
            return {}
        results: Dict[str, str] = {}
        for key, snap in self.snapshots.items():
            p = Path(snap.path)
            try:
                if snap.existed:
                    if snap.content is None:
                        results[key] = "restored (empty - content unreadable at snapshot)"
                        p.write_bytes(b"")
                    else:
                        p.write_bytes(snap.content)
                        results[key] = "restored from snapshot"
                else:
                    if p.exists():
                        p.unlink()
                        results[key] = "deleted (did not exist before transaction)"
                    else:
                        results[key] = "already absent"
            except Exception as e:
                results[key] = f"ROLLBACK FAILED: {e}"
        self.snapshots.clear()
        return results

    @property
    def size(self) -> int:
        return len(self.snapshots)
