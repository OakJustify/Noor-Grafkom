"""Witness the actual campaign with input-only controls and save visual evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import cairo
import numpy as np
import pygame
import pymunk

from .game import Game, ROOT, SIZE
from .levels import LEVELS
from .physics import Input
from .pilot import Pilot


def verify(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    game = Game(0, persist=False)
    captures, milestones, trace, solved = [], set(), [], []
    mechanics, additional_captures = {}, set()
    rope_start = None
    floating_start = None
    beam_angles = []
    start = time.perf_counter()

    def capture(name):
        path = output / (name + ".png")
        game.draw()
        pygame.image.save(game.canvas, path)
        pixels = pygame.surfarray.array3d(game.canvas)
        assert pixels.std() > 12, f"Blank/low-contrast render: {path}"
        captures.append({"name": name, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "pixel_std": round(float(pixels.std()), 2), "physics": game.world.snapshot()})

    try:
        capture("00-title")
        game.help = True
        capture("00-controls")
        game.help = False
        game.start(0)
        pilot = Pilot(0)
        for frame in range(6000):
            pygame.event.pump()
            if game.world.chapter != pilot.chapter:
                pilot = Pilot(game.world.chapter)
            control = pilot.control(game.world)
            before_gravity = game.world.gravity
            game.update(1 / 60, control)
            w = game.world
            # A transition loads a fresh world but does not simulate it with
            # this frame's old-room input. Observe it only after its own pilot
            # has been selected; phase names can overlap between rooms.
            if w.chapter != pilot.chapter:
                continue
            if w.chapter == 1 and w.grab_kind == "rope":
                if rope_start is None:
                    rope_start = w.rope_distance
                if rope_start - w.rope_distance > 35:
                    mechanics.setdefault("climb_height_choice", {"frame": frame, "climbed_px": round(rope_start - w.rope_distance, 2)})
            if w.chapter == 2:
                if w.cover_fraction == 1 and w.water_active:
                    mechanics.setdefault("opening_exposed_and_valve_filling", {"frame": frame, "water_surface": w.water_surface})
                if w.support == w.crates[0].body:
                    if floating_start is None:
                        floating_start = w.player.position.y
                    if floating_start - w.player.position.y > 50:
                        mechanics.setdefault("box_carries_player_up_with_water", {"frame": frame, "rise_px": round(floating_start - w.player.position.y, 2)})
                if w.cover_fraction == 1 and w.water_active and w.water_surface > 480 and "water-before" not in additional_captures:
                    capture("03-open-cover-before-rise")
                    additional_captures.add("water-before")
            if w.chapter == 4 and before_gravity == -1 and w.gravity == 1 and not control.action:
                mechanics["gravity_expires_without_second_relay"] = {"frame": frame, "seconds_remaining": w.gravity_remaining}
                capture("05-gravity-return")
            if w.chapter == 3:
                beam_angles.append(w.beam.body.angle)
                if pilot.phase == "exit" and "oscillation_then_crest_departure" not in mechanics:
                    mechanics["oscillation_then_crest_departure"] = {
                        "frame": frame, "reversals": pilot.seesaw.reversals,
                        "angle_range_rad": round(max(beam_angles) - min(beam_angles), 4),
                         "departure_angle_rad": round(w.beam.body.angle, 4)}
            if w.magnet:
                if w.magnet.captured and "magnet-contact" not in additional_captures:
                    capture("06-first-magnetic-contact")
                    additional_captures.add("magnet-contact")
                if (sorted(w.magnet.captured) == [0] and w.magnet.box_gravity == 1
                        and w.support == w.crates[1].body):
                    mechanics.setdefault("magnetic_split_height_route", {
                        "frame": frame, "held_blocks": [1], "support_block": 2,
                        "player_gravity": w.gravity, "box_gravity": w.magnet.box_gravity,
                        "block_heights_y": [round(p.body.position.y, 3) for p in w.crates],
                        "contacts": list(w.magnet.capture_history),
                    })
            if frame % 30 == 0:
                trace.append({"frame": frame, "pilot_phase": pilot.phase, "state": game.state, **w.snapshot()})
            if w.dead:
                raise AssertionError(f"Input-only campaign pilot died: {w.snapshot()}")
            name = None
            if w.chapter == 0 and w.gate_open and w.player.position.x > 1020:
                name = "01-pressure-gate"
            elif w.chapter == 1 and w.grab_kind == "rope" and w.player.position.x > 865:
                name = "02-rope-momentum"
            elif w.chapter == 2 and w.support == w.crates[0].body and w.water_surface < 390:
                name = "03-rising-water"
            elif w.chapter == 3 and pilot.phase == "exit" and w.beam.body.angle < -0.25:
                name = "04-oscillating-platform"
            elif w.chapter == 4 and w.gravity == -1 and w.player.position.x > 865:
                name = "05-inverted-gravity"
            elif w.magnet and w.support == w.crates[1].body and sorted(w.magnet.captured) == [0]:
                name = "06-split-height-route"
            if name and name not in milestones:
                capture(name)
                milestones.add(name)
            if w.complete and w.chapter not in [s["chapter_index"] for s in solved]:
                solved.append({"chapter_index": w.chapter, "simulation_seconds": round(w.time, 3), "final": w.snapshot()})
            if game.state == "ending":
                capture("07-ending")
                break
        assert game.state == "ending", game.world.snapshot()
        assert len(solved) == len(LEVELS) and len(milestones) == len(LEVELS)
        assert set(mechanics) >= {"climb_height_choice", "opening_exposed_and_valve_filling",
                                  "box_carries_player_up_with_water", "gravity_expires_without_second_relay",
                                  "oscillation_then_crest_departure", "magnetic_split_height_route"}
        campaign_frames = frame + 1
        game.start(0)
        game.state = "paused"
        capture("08-pause")
        game.start(1)
        while not game.world.dead:
            game.world.step(Input(move=1))
        game.death_timer = 0.8
        game.visual_time = game.world.time
        game.camera = max(0, game.world.player.position.x - 360)
        capture("09-fall-and-retry")

        assets = []
        for path in sorted((ROOT / "assets" / "echo").rglob("*")):
            if not path.is_file():
                continue
            record = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            if path.suffix == ".wav":
                with wave.open(str(path)) as sound:
                    record.update(channels=sound.getnchannels(), sample_rate=sound.getframerate(),
                                  seconds=round(sound.getnframes() / sound.getframerate(), 3))
                    pcm = np.frombuffer(sound.readframes(sound.getnframes()), dtype="<i2")
                    record["peak"] = int(np.abs(pcm.astype(np.int32)).max())
                    assert 0 < record["peak"] < 32767, record
            assets.append(record)
        assert len([a for a in assets if a["path"].endswith(".wav")]) >= 9
        assert len([a for a in assets if a["path"].endswith(".png")]) >= 8
        assert any(a.get("seconds", 0) >= 24 for a in assets)

        contact = pygame.Surface((960, ((len(captures) + 1) // 2) * 290))
        contact.fill((9, 14, 17))
        for i, c in enumerate(captures):
            image = pygame.image.load(c["path"])
            small = pygame.transform.smoothscale(image, (480, 270))
            x, y = i % 2 * 480, i // 2 * 290
            contact.blit(small, (x, y))
            label = pygame.font.Font(None, 18).render(c["name"], True, (190, 213, 201))
            contact.blit(label, (x + 12, y + 273))
        pygame.image.save(contact, output / "contact-sheet.png")
        report = {"success": True, "method": "Actual Game.update at 60 Hz; fixed 120 Hz physics; Pilot emits only movement/jump/grab/action/climb inputs.",
                   "no_teleports_in_campaign": True, "campaign_reached_ending": True,
                   "mechanics_witness": mechanics,
                   "reference_equivalence_claimed": False,
                  "solved_rooms": solved, "campaign_frames": campaign_frames,
                  "wall_seconds": round(time.perf_counter() - start, 3),
                  "libraries": {"pygame": pygame.version.ver, "cairo": cairo.cairo_version_string(), "pymunk": pymunk.version, "numpy": np.__version__},
                  "captures": captures, "assets": assets, "trace": trace}
        report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((ROOT / "echo_game").glob("*.py"))}
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: report[k] for k in ("success", "method", "campaign_reached_ending", "campaign_frames", "wall_seconds", "libraries")}, indent=2))
        print("Solved room simulation times:", [r["simulation_seconds"] for r in solved])
        print(f"Verified {len(assets)} asset files; saved {len(captures)} screenshots to {output}")
        return report
    finally:
        game.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "echo" / "verification")
    args = parser.parse_args()
    verify(args.output)


if __name__ == "__main__":
    main()
