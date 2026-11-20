"""Exercise the evidence writer through real room transitions, not staged state."""

import hashlib
import json
from pathlib import Path

from echo_game.verify import verify
from echo_game.levels import LEVELS


def test_campaign_evidence_covers_current_mechanics_and_sources(tmp_path):
    report = verify(tmp_path)
    assert report["success"] and report["campaign_reached_ending"]
    assert not report["reference_equivalence_claimed"]
    assert report["no_teleports_in_campaign"]
    assert [room["chapter_index"] for room in report["solved_rooms"]] == list(range(len(LEVELS)))
    assert report["campaign_frames"] < 4800
    witness = report["mechanics_witness"]
    assert witness["climb_height_choice"]["climbed_px"] > 35
    assert witness["box_carries_player_up_with_water"]["rise_px"] > 50
    assert witness["gravity_expires_without_second_relay"]["seconds_remaining"] == 0
    crest = witness["oscillation_then_crest_departure"]
    assert crest["reversals"] >= 4 and crest["angle_range_rad"] > 0.65
    assert crest["departure_angle_rad"] < -0.26
    magnet = witness["magnetic_split_height_route"]
    assert magnet["held_blocks"] == [1] and magnet["support_block"] == 2
    assert magnet["player_gravity"] == magnet["box_gravity"] == 1
    assert magnet["block_heights_y"][0] < magnet["block_heights_y"][1] - 100
    captures = {capture["name"]: capture for capture in report["captures"]}
    assert "04-oscillating-platform" in captures
    assert captures["04-oscillating-platform"]["physics"]["crates"] == []
    assert captures["06-split-height-route"]["physics"]["magnet"]["captured"] == [0]
    assert (tmp_path / "contact-sheet.png").is_file()
    assert json.loads((tmp_path / "verification.json").read_text()) == report
    for capture in captures.values():
        assert hashlib.sha256(Path(capture["path"]).read_bytes()).hexdigest() == capture["sha256"]
    root = Path(__file__).resolve().parents[1]
    for path, digest in report["source_sha256"].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
