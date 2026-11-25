# CHANGELOG — NUR v4

Catatan perubahan bersifat kronologis. Angka hasil pengujian dirinci di
`07-testing.md` dan `docs/verification/`.

## 2026-11-25 — Modularisasi per tanggung jawab

- `puzzles.py`, `game.py`, `engine.py`, `art.py`, `audio.py`,
  `spawn_manager.py`, `sanity.py`, dan `hallucinations.py` dipecah menjadi paket
  dengan satu berkas per tanggung jawab; API publik tetap di
  `nur_game.<nama>`.
- Alias `puzzle_components.py` dan `puzzle_manager.py` dihapus (tidak ada
  pengguna).
- `__main__.py` kini dijaga dengan `if __name__ == "__main__":` sehingga
  mengimpor paket tidak memulai game.
- `_source_hashes()` kini meng-hash seluruh `*.py` secara rekursif agar berkas
  di subpaket masuk ke bukti verifikasi.
- `tests/v4/test_depth_and_hazards.py` memakai `rglob` saat memindai sumber.

## 2026-11-25 — Perapian struktur folder

- Merapikan root menjadi `assets/`, `docs/`, `src/`, `tests/` sesuai permintaan.
- Memindahkan kode ke `src/nur_game/`, script ke `src/scripts/`, launcher ke
  `src/play_nur.py`; `config.ROOT` kini `parents[2]`.
- Memindahkan data konten ke `assets/content/` dan menambah `config.CONTENT_DIR`;
  `load_puzzle_catalog()` tidak lagi bergantung pada direktori kerja.
- Menggabungkan `tests_v4/` dan `tests_nur/` menjadi `tests/v4/` dan `tests/nur/`;
  `pytest.ini` memakai `pythonpath = src` dan `testpaths = tests`.
- Menyusun dokumen bernomor: `03-architecture.md`, `06-planning.md`,
  `07-testing.md`, serta menambah `04-design.md`, `05-specifications.md`,
  `08-ai-guidelines.md`, `09-decisions.md`, `CHANGELOG.md`, dan `docs/README.md`.
- Memindahkan bukti verifikasi ke `docs/verification/` (termasuk hasil polish
  freebuff di `docs/verification/nur/`).

## 2026-11-25 — Gabungan O1–O3 dan F1–F4

- `src/scripts/validate_content.py` kini membaca
  `nur_game.puzzles.COMPONENT_CLASSES` sebagai allowlist komponen nyata.
- `tests/v4/test_content_catalogs.py` memeriksa kecocokan 26 spec dengan 22
  komponen F4, membangun setiap spec saat runtime, dan menguji pemuatan katalog
  dari direktori lain.
- `README.md` dan `assets/content/README.md` diperbarui dengan peta gabungan
  serta perintah regenerate/validasi.
- Alias `puzzle_components.py` dan `puzzle_manager.py` saat itu dipertahankan
  untuk kompatibilitas, lalu dihapus pada entri modularisasi di atas.

## 2026-11-25 — Sistem F1–F4 (freebuff)

- F1: animasi monster bilateral dan state Patrol → Detect → Flee → Return di
  `monsters.py`/`encounters.py`.
- F2: spawn manager dinamis dengan pool dan maksimal 8 kandidat per wilayah.
- F3: sistem akal/halusinasi di `sanity.py`, tombol H, HUD, dan save/load.
- F4: framework puzzle di `puzzles.py` dengan 22 komponen dan generate_from_spec.

## 2026-11-25 — Konten O1–O3

- 33 prefab platform (10 kategori) dan 32 prefab obstacle (10 kategori) sebagai
  JSON di `assets/content/`, lengkap dengan `PLATFORM_LIBRARY.md` dan
  `OBSTACLE_LIBRARY.md`.
- 26 spesifikasi puzzle di 12 kategori, `schema.json`, dan `puzzle_index.md`.
- Generator deterministik `src/scripts/generate_content.py` dan validator
  tanpa dependency `src/scripts/validate_content.py`.
- Perbaikan hasil validasi: toleransi batas float, noise
  `ToyCluster_Plushies` `.30` → `.56`, dan dependensi `puzzle_003` dari
  `Obstacle_BoxCrate_Wooden` menjadi `Platform_BoxCrate_Wooden`.

## 2026-11-24 — Revisi v4

- Controller kontinu menggantikan ruang terpisah; 29 wilayah/112.360 px dalam
  satu Pymunk space.
- Empat lapisan kedalaman depan ke belakang dengan parallax dan arsitektur opak.
- 28 mesin mematikan, delapan bentuk monster, stasiun sumbu tanpa NPC,
  glide berbasis stamina, dan audio sintetis tiga lapis.
- `baseline_game.py` dan tes room-based dipertahankan sebagai regresi; save v4
  dipisah ke `saves/nur-v4.json`.
