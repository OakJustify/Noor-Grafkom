# v3 games

## NÜR — main game yang baru

NÜR sekarang mempunyai **campaign 29 ruangan**, termasuk empat babak baru di
desa, arsip, hutan, dan lingkungan perawatan. **Menjalankan `play_echo.py`
masih membuka ECHO lama**—itu disengaja supaya baseline dan test regresinya
tetap utuh. Untuk memainkan NÜR, gunakan entrypoint ini:

```bash
cd ~/Projects/03-projects/02-games/noor-grafkom/v3
.venv-echo/bin/python play_nur.py
```

Kontrol: **A/D** jalan, **Space/W/↑** lompat, **E** interaksi, **ESC** jeda,
**R** ulang ruangan, **M** bisu. Tahan **E** untuk menarik krate atau memegang
tali; **W/S** memanjat tali, **Space** melepas dengan lompatan. Pemain langsung
spawn di rumah; petunjuk kecil hanya muncul dekat objek yang bisa dipakai.
**J** membuka jurnal/peta dan menghentikan simulasi; **←/→** mengganti halaman.
Tekan-lepas **E** untuk memilih komponen, mengubah saklar, memainkan nada atau
memutar cermin. Tahan E hanya untuk menarik krate/memegang tali.

Progress puzzle dan catatan disimpan otomatis di checkpoint. Lanjutkan dengan
**C** di menu atau:

```bash
.venv-echo/bin/python play_nur.py --continue
```

Playtest input-only pada physics asli selesai dalam **19 menit 28 detik waktu
game**, tanpa kematian atau delay membaca yang ditambahkan. Itu adalah run
otomatis dengan jawaban sudah diketahui, bukan ukuran waktu/fun pemain manusia.
Laporan, batasan dan screenshot aktual: [`docs/nur/verification/PLAYTEST.md`](docs/nur/verification/PLAYTEST.md).

Lentera yang dibawa selalu melindungi dari monster, termasuk proyektil boss,
bahkan ketika muatannya habis. Bayangan mundur dan memudar saat didekati.
Gergaji dan jurang tetap berbahaya: tantangan datang dari rute rak, puzzle
krate/pelat, ayunan tali, rangkaian, debit air, urutan nada dan jalur cahaya,
bukan tabrakan dengan monster.

Rincian desain, sistem lilin, dan kredit audio CC0 ada di
[`docs/nur/README.md`](docs/nur/README.md).

---

## ECHO: The Hollow Signal (baseline yang dipertahankan)

An original six-room physics puzzle-platformer built with **Pygame, Pycairo,
Pymunk and NumPy**. Includes generated characters, layered artwork, original
music and sound, checkpoints, an input-only demo, and seeded procedural Endless
rooms with generated layouts, multi-stage physics puzzles and layered scenery.

## Play

```bash
cd ~/Projects/03-projects/02-games/noor-grafkom/v3
.venv-echo/bin/python play_echo.py
```

**A/D** to walk, **Space** to jump, **E/Ctrl** to grab or operate a nearby
mechanism, **W/S** to climb a held rope, **R** to retry the current room,
**F1** to toggle Endless details, and **H** for help.

Press **E** at the title, or launch directly:

```bash
.venv-echo/bin/python play_echo.py --endless --seed 7
```

Endless does **not** shuffle six fixed Campaign rooms. Each room composes two
to four stages: push/pull crate relays around a water lift, rope crossing,
seesaw bridge, inverted corridor or magnetic stair. Dimensions, elevations,
object positions and stage order change with the seed. Exact layout, puzzle
and background signatures cannot repeat within a run. The six mechanics are
reused; this is not a promise of an entirely new physics rule in every room.

Only candidates solved from spawn to exit using ordinary inputs in the live
120 Hz Pymunk simulation are accepted. Simple walking/jumping and
no-interaction bypasses are probed as well. **R** replays the same generated
room; reaching its signal generates the next one.

The courier, props, lighting and HUD retain Campaign styling, while Cairo
generates new parallax silhouettes, sky, fog and particles for each room.
**F1**, or `--show-hud`, reveals the seed and room ID.

```bash
.venv-echo/bin/python play_echo.py --endless --seed 7 --show-hud
```

Room verification runs before loading and can take a few seconds. The earlier
streaming forest/health/lantern system remains available internally for regression
tests, but it is no longer the default Endless mode or exposed via density flags.
The default launch and **Enter** still select the six-room campaign, not endless.

Try the magnetic ceiling puzzle directly:

```bash
.venv-echo/bin/python play_echo.py --chapter 6 --play --no-save
```

- [Setup, controls and all six rooms](docs/echo/README.md)
- [Reference behavior compared with the implementation](docs/echo/REFERENCE_COMPARISON.md)
- [Verification results](docs/echo/verification/README.md)
- [Procedural room design and verification boundaries](docs/procedural_puzzle_design.md)
- [Historical streaming-mode generation repairs](docs/echo/verification/generation-repair/README.md)
- [Campaign screenshots](docs/echo/verification/contact-sheet.png)

The supplied LIMBO installation informed the mechanical research. Playing ECHO
requires no LIMBO files. Its native solver has not been recovered; ECHO uses
documented qualitative behaviors and original geometry/assets.
