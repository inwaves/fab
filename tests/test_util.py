from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fab.errors import RegistryError
from fab.util import (
    append_unique,
    compact_id,
    current_time,
    ensure_safe_id,
    format_datetime,
    normalize_string_list,
    parse_datetime,
    read_json,
    utc_now,
    write_json,
)


class DatetimeTest(unittest.TestCase):
    def test_date_only_is_utc_midnight(self) -> None:
        self.assertEqual(parse_datetime("2026-05-07"), datetime(2026, 5, 7, tzinfo=timezone.utc))

    def test_offsets_naive_and_z_suffix_normalise_to_utc(self) -> None:
        expected = datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_datetime("2026-05-07T10:00:00Z"), expected)
        self.assertEqual(parse_datetime("2026-05-07T12:00:00+02:00"), expected)
        self.assertEqual(parse_datetime(" 2026-05-07T10:00:00 "), expected)

    def test_rejects_empty_and_unparseable_values(self) -> None:
        for value in ("", "   "):
            with self.assertRaisesRegex(RegistryError, "empty datetime"):
                parse_datetime(value)
        with self.assertRaisesRegex(RegistryError, "invalid datetime: next tuesday"):
            parse_datetime("next tuesday")

    def test_now_helpers_round_trip(self) -> None:
        stamp = utc_now()
        self.assertTrue(stamp.endswith("Z"))
        self.assertLess(abs((parse_datetime(stamp) - current_time()).total_seconds()), 5)
        self.assertEqual(current_time().microsecond, 0)

        eastern = datetime(2026, 5, 7, 8, 0, tzinfo=timezone(timedelta(hours=-2)))
        self.assertEqual(format_datetime(eastern), "2026-05-07T10:00:00Z")


class JsonIoTest(unittest.TestCase):
    def test_read_json_reports_missing_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            with self.assertRaisesRegex(RegistryError, "not found"):
                read_json(missing)

            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(RegistryError, "invalid JSON in"):
                read_json(broken)

    def test_write_json_creates_parents_and_sorts_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "deeper" / "data.json"

            write_json(path, {"b": 1, "a": [2]})

            self.assertEqual(path.read_text(encoding="utf-8"), '{\n  "a": [\n    2\n  ],\n  "b": 1\n}\n')
            self.assertEqual(read_json(path), {"a": [2], "b": 1})


class IdentifierTest(unittest.TestCase):
    def test_compact_id_continues_from_highest_match(self) -> None:
        self.assertEqual(compact_id("ws", []), "ws_001")
        self.assertEqual(compact_id("ws", ["ws_007", "ws_3", "pkt_010", "junk", "ws_x"]), "ws_008")
        self.assertEqual(compact_id("ws", ["ws_999"]), "ws_1000")

    def test_ensure_safe_id_accepts_path_safe_segments_only(self) -> None:
        for value in ("ws_001", "A-b_9", "7"):
            ensure_safe_id("thing", value)
        for value in ("", "../x", "a/b", "-leading", ".hidden", "with space", None, 5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RegistryError, f"invalid thing: {value}"):
                    ensure_safe_id("thing", value)


class ListHelperTest(unittest.TestCase):
    def test_normalize_string_list_accepts_scalars_and_drops_falsy_items(self) -> None:
        self.assertEqual(normalize_string_list(None, label="x"), [])
        self.assertEqual(normalize_string_list("one", label="x"), ["one"])
        self.assertEqual(normalize_string_list(["a", "", None, 3], label="x"), ["a", "3"])
        with self.assertRaisesRegex(RegistryError, "caveats must be a list"):
            normalize_string_list({"a": 1}, label="caveats")

    def test_append_unique_skips_falsy_and_repeated_values(self) -> None:
        values: list[object] = ["a"]

        append_unique(values, ["a", "b", "", None, "b", {"id": 1}, {"id": 1}])

        self.assertEqual(values, ["a", "b", {"id": 1}])


if __name__ == "__main__":
    unittest.main()
