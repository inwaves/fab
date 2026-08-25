from __future__ import annotations

import unittest

from fab.errors import RegistryError
from fab.status import (
    STATUS_FOR_ACTION,
    STATUS_TRANSITIONS,
    TERMINAL_STATUSES,
    VALID_DECISION_ACTIONS,
    VALID_STATUSES,
    ensure_decision_action,
    ensure_status,
    ensure_status_transition,
    normalize_decision_target,
    status_after_for_action,
)


class StatusTransitionTest(unittest.TestCase):
    def test_transition_table_covers_every_status(self) -> None:
        self.assertEqual(set(STATUS_TRANSITIONS), set(VALID_STATUSES))
        for targets in STATUS_TRANSITIONS.values():
            self.assertTrue(targets <= VALID_STATUSES)

    def test_same_status_is_always_allowed(self) -> None:
        for status in VALID_STATUSES:
            ensure_status_transition(status, status)

    def test_terminal_statuses_have_no_exits(self) -> None:
        for status in TERMINAL_STATUSES:
            self.assertEqual(STATUS_TRANSITIONS[status], frozenset())
            for target in VALID_STATUSES - {status}:
                with self.assertRaisesRegex(RegistryError, f"{status} is terminal"):
                    ensure_status_transition(status, target)

    def test_disallowed_moves_list_the_alternatives(self) -> None:
        with self.assertRaisesRegex(RegistryError, "planned -> completed; allowed: paused, quarantined, running, stopped"):
            ensure_status_transition("planned", "completed")
        with self.assertRaisesRegex(RegistryError, "quarantined -> completed"):
            ensure_status_transition("quarantined", "completed")

    def test_unknown_starting_status_is_rejected(self) -> None:
        with self.assertRaisesRegex(RegistryError, "invalid status: None"):
            ensure_status_transition(None, "running")

    def test_every_action_resolves_to_a_valid_status(self) -> None:
        for action in VALID_DECISION_ACTIONS:
            after = status_after_for_action(action, "running")
            self.assertIn(after, VALID_STATUSES)
            if action in STATUS_FOR_ACTION:
                self.assertEqual(after, STATUS_FOR_ACTION[action])
            else:
                self.assertEqual(after, "running")


class DecisionTargetTest(unittest.TestCase):
    live_state = {"artifacts": [{"id": "art_001", "claims": [{"id": "claim_a"}]}]}

    def test_status_and_action_validation(self) -> None:
        ensure_status("running")
        ensure_decision_action("escalate")
        with self.assertRaisesRegex(RegistryError, "invalid status: done"):
            ensure_status("done")
        with self.assertRaisesRegex(RegistryError, "invalid judgment action: ship; valid: complete, continue"):
            ensure_decision_action("ship")

    def test_workstream_target_defaults_to_the_workstream(self) -> None:
        self.assertEqual(
            normalize_decision_target(self.live_state, "ws_001", "workstream", None),
            {"type": "workstream", "id": "ws_001"},
        )
        self.assertEqual(
            normalize_decision_target(self.live_state, "ws_001", "workstream", "ws_001"),
            {"type": "workstream", "id": "ws_001"},
        )
        with self.assertRaisesRegex(RegistryError, "workstream judgment target must be ws_001"):
            normalize_decision_target(self.live_state, "ws_001", "workstream", "ws_002")

    def test_artifact_and_claim_targets_must_exist(self) -> None:
        self.assertEqual(
            normalize_decision_target(self.live_state, "ws_001", "artifact", "art_001"),
            {"type": "artifact", "id": "art_001"},
        )
        self.assertEqual(
            normalize_decision_target(self.live_state, "ws_001", "claim", "art_001/claim_a"),
            {"type": "claim", "id": "art_001/claim_a"},
        )
        with self.assertRaisesRegex(RegistryError, "invalid judgment target type: paper"):
            normalize_decision_target(self.live_state, "ws_001", "paper", "x")
        with self.assertRaisesRegex(RegistryError, "target id is required for artifact judgment"):
            normalize_decision_target(self.live_state, "ws_001", "artifact", None)
        with self.assertRaisesRegex(RegistryError, "artifact target not found: art_404"):
            normalize_decision_target(self.live_state, "ws_001", "artifact", "art_404")
        with self.assertRaisesRegex(RegistryError, "claim target not found: art_001/claim_x"):
            normalize_decision_target(self.live_state, "ws_001", "claim", "art_001/claim_x")


if __name__ == "__main__":
    unittest.main()
