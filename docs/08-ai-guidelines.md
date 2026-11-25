# 08 — Panduan untuk agen AI

Dokumen ini berisi aturan kerja untuk manusia maupun agen yang menyunting v4.
Tujuannya menjaga agar perubahan tetap bisa diverifikasi dan tidak merusak
kontrak yang sudah disepakati di `09-decisions.md`.

## 1. Kenali checkout ini

Ini adalah game **Python/Pygame**, bukan proyek Unity. Tidak ada `Assets/`,
file `.cs`, `.prefab`, `.unity`, atau `.controller`, dan tidak ada `GameManager`
atau `LanternController` Unity. Spesifikasi tugas memakai istilah Unity; terjemahkan
ke padanan Python/JSON menurut `05-specifications.md`.

**Jangan** membuat proyek Unity tiruan, file `.cs` kosong, atau placeholder
`Assets/` hanya untuk "memenuhi struktur". Itu menambah file tanpa menambah
fungsi dan akan gagal saat dijalankan.

## 2. Sumber kebenaran konten

- `src/scripts/generate_content.py` adalah satu-satunya tempat mengedit tabel
  platform, obstacle, dan puzzle.
- File di `assets/content/platforms/generated/`,
  `assets/content/obstacles/generated/`, `puzzle_index.md`, dan library index
  adalah **hasil generasi**. Jangan disunting langsung; perbaiki tabel lalu
  jalankan generator.
- `assets/content/puzzles/schema.json` dan `README.md` di `assets/content/`
  ditulis manual dan boleh disunting langsung.

Selalu jalankan urutan ini setelah mengubah konten:

```bash
.venv-nur/bin/python src/scripts/generate_content.py
.venv-nur/bin/python src/scripts/validate_content.py
.venv-nur/bin/python -m pytest -q tests/v4/test_content_catalogs.py
```

## 3. Validasi menyentuh implementasi nyata

`src/scripts/validate_content.py` membaca `nur_game.puzzles.COMPONENT_CLASSES`
sebagai allowlist komponen. Jika menambah/menghapus komponen F4, perbarui katalog
**dan** registry secara bersamaan; tes `test_puzzle_catalog_matches_f4_registry`
akan menolak ketidaksesuaian. Jangan menambah nama komponen hanya agar validator
lolos tanpa implementasinya.

## 4. Path dan impor

- Gunakan konstanta dari `src/nur_game/config.py`. `ROOT` sudah
  `Path(__file__).resolve().parents[2]` karena package berada di `src/`.
- Jangan memakai `Path("content")`, `Path("docs")`, atau path relatif lain yang
  bergantung pada direktori kerja. `load_puzzle_catalog()` sudah memakai
  `config.CONTENT_DIR`; tes membuktikan katalog tetap terbaca dari `/tmp`.
- `pytest.ini` menetapkan `pythonpath = src`. Jalankan pytest dari root v4
  dengan `.venv-nur/bin/python -m pytest -q`, bukan `python tests/...`.
- Script yang dijalankan langsung tetapi mengimpor `nur_game` perlu
  `PYTHONPATH=src` bila tidak memakai launcher.
- Modul dengan beberapa tanggung jawab (penciptaan dunia, simulasi, rendering,
  penyimpanan, CLI) dipecah menjadi paket, satu berkas per tanggung jawab. Nama
  publik tetap diekspor dari `nur_game.<nama>` agar pemanggil tidak berubah.
  Berkas yang memang satu fungsi/data kohesif (tabel `story.py`, `levels.py`,
  `scripts/generate_content.py`, tabel komponen puzzle) tidak dipecah hanya
  karena panjang.

## 5. Struktur folder

```
assets/  → aset dan data konten (bukan kode)
docs/    → dokumentasi bernomor + bukti verifikasi
src/     → package nur_game, scripts, launcher
tests/   → nur/ (regresi lama) dan v4/ (kontinu + konten)
```

Tambah folder baru hanya bila ada kebutuhan nyata, lalu catat di
`README.md` dan `05-specifications.md`. Dua subfolder tes sengaja dipisah karena
fixture `game` keduanya berbeda kontrak: `tests/nur` memakai `baseline_game.Game`
(room-based), `tests/v4` memakai `game.Game` (kontinu). Jangan menggabungkan
keduanya atau menghapus `baseline_game.py`.

## 6. Dokumentasi

- `docs/README.md` adalah indeks; tautan di dalamnya harus relatif terhadap
  `docs/`.
- Nama file mengikuti pola `NN-topik.md` persis seperti di `01-overview.md`.
  Jangan menulis `02-requirements.md` (plural) atau membuat `docs/docs/`.
- `verification/` berada di dalam `docs/`; `VERIFICATION.md` sudah berganti
  nama menjadi `07-testing.md`, `ARCHITECTURE.md` menjadi `03-architecture.md`.
  Perbarui tautan bila memindahkan file.

## 7. Git dan klaim kerja

Checkout ini **bukan repository git**. Jangan mengaku sudah commit, branch,
atau membuat pull request. Nyatakan perubahan sebagai file yang ditulis di
working tree. Bila repository git tersedia kemudian, baru gunakan alur normal.

## 8. Verifikasi akhir

Sebelum melaporkan selesai, jalankan minimal:

```bash
.venv-nur/bin/python src/scripts/validate_content.py
.venv-nur/bin/python -m pytest -q
.venv-nur/bin/python src/play_nur.py --headless --frames 120 --no-save --mute --report /tmp/smoke.json
```

Laporkan hasil apa adanya. Bedakan "terverifikasi oleh pilot otomatis" dari
"playtest manusia"; lihat batas kualitas di `README.md` root dan
`07-testing.md`. Jangan mengklaim kualitas artistik, aksesibilitas, atau efek
medis yang belum diuji.
