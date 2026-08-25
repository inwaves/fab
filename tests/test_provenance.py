from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fab.provenance import git_commit_for_path, git_dirty, git_head, git_output, sha256_file, sha256_path


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=test@example.com", "-c", "user.name=Test", *args],
        check=True,
        capture_output=True,
        text=True,
    )


class Sha256Test(unittest.TestCase):
    def test_sha256_variants_agree_and_handle_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("hello\n", encoding="utf-8")

            digest = sha256_file(path)

            self.assertEqual(len(digest or ""), 64)
            self.assertEqual(sha256_path(path), f"sha256:{digest}")
            self.assertIsNone(sha256_file(Path(tmp) / "missing.md"))
            self.assertIsNone(sha256_file(Path(tmp)))
            with self.assertRaises(FileNotFoundError):
                sha256_path(Path(tmp) / "missing.md")


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class GitProvenanceTest(unittest.TestCase):
    def test_clean_repo_reports_false_not_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            git(repo, "init", "-q")
            note = repo / "note.md"
            note.write_text("# Note\n", encoding="utf-8")
            git(repo, "add", "note.md")
            git(repo, "commit", "-q", "-m", "init")

            head = git_head(repo)

            self.assertEqual(git_output(repo, "status", "--short"), "")
            self.assertIs(git_dirty(repo), False)
            self.assertRegex(head or "", r"^[0-9a-f]{40}$")
            self.assertEqual(git_commit_for_path(repo, note), head)

            (repo / "scratch.md").write_text("wip\n", encoding="utf-8")
            self.assertIs(git_dirty(repo), True)

    def test_non_repo_and_foreign_paths_report_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.mkdir()

            self.assertIsNone(git_output(plain, "rev-parse", "HEAD"))
            self.assertIsNone(git_head(plain))
            self.assertIsNone(git_dirty(plain))
            self.assertIsNone(git_commit_for_path(plain, Path(tmp) / "elsewhere.md"))
            self.assertIsNone(git_head(Path(tmp) / "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
