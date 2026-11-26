# Status proyek — NUR / freebuff

Status terkini task F1–F4 dan hasil gabungannya dengan konten O1–O3.
Rincian tiap task ada di [06-planning.md](06-planning.md); alasan keputusan ada
di [09-decisions.md](09-decisions.md).

Adaptasi naskah pada branch `cutscene`: pembuka, enam fragmen/cutscene memori,
void hitam total, ending Nur–Dara, subtitle Indonesia tanpa dubbing, galeri
replay, pemudaran terpisah dari lentera, dan checkpoint cerita. Rincian serta
metode verifikasi ada di [10-story-cinematics.md](10-story-cinematics.md).

## Status task

| ID | Task | Status | Mulai | Implementasi |
|---|---|---|---|---|
| F1 | Monster bilateral animation & flee AI | `done` | 2026-11 | `src/nur_game/monsters.py`, `src/nur_game/encounters.py` |
| F2 | Dynamic monster spawn manager | `done` | 2026-11 | `src/nur_game/spawn_manager/` |
| F3 | Hallucination & sanity system | `done` | 2026-11 | `src/nur_game/sanity/`, tombol H, HUD, save/load |
| F4 | Puzzle framework & 20+ implementations | `done` | 2026-11 | `src/nur_game/puzzles/` (22 komponen) |

## Arah yang dipilih

Opsi **1 — adaptasi ke Python/Pygame v4** dipilih dan sudah dikerjakan.
Spesifikasi memakai kontrak Unity (`Assets/Scripts/...`, prefab, `.controller`,
`LanternController`, `GameManager`, layer/tag Unity), tetapi checkout ini adalah
game Python/Pygame:

- Tidak ada `Assets/`, file `.cs`, `.unity`, `.prefab`, atau `.controller`.
- Tidak ada `LanternController`, `GameManager`, `PlayerController`, atau
  `InputManager` Unity.
- Checkout sekarang memakai Git pada branch `cutscene`; implementasi ini tidak
  membuat commit, PR, atau push. Catatan pemetaan Unity tetap berlaku.
- `assets/content/README.md` mencatat pemetaan yang sama untuk O1–O3: data Unity
  ditulis ulang sebagai JSON netral di `assets/content/`.

Opsi 2 (pindah ke repo Unity nyata) dan opsi 3 (hanya menyimpan daftar task)
tidak diambil.

## Hasil gabungan

- 33 platform, 32 obstacle, dan 26 puzzle dari O1–O3 berada di
  `assets/content/` dan divalidasi terhadap komponen F4 yang sebenarnya.
- `src/scripts/validate_content.py` membaca registry
  `nur_game.puzzles.COMPONENT_CLASSES`; tes di `tests/v4/` membangun setiap
  spec saat runtime.
- Status verifikasi dan angka hasil pengujian ada di
  [07-testing.md](07-testing.md).

## Catatan integrasi

`spawn_manager/` (F2) dan framework `puzzles/` (F4) tersedia sebagai paket
dan terhubung ke katalog konten, tetapi belum dipanggil dari loop utama
`src/nur_game/game/`. Menghubungkannya mengubah gameplay dan memerlukan
keputusan desain tersendiri.
