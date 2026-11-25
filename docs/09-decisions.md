# 09 — Keputusan dan alasan

Ringkasan keputusan yang membentuk v4. Bila ada konflik antar dokumen, keputusan
di sini yang dipakai, kecuali `05-specifications.md` untuk angka implementasi.

## D1 — Terjemahkan kontrak Unity ke Python/JSON

**Keputusan:** Task O1–O3 dan F1–F4 diadaptasi dari istilah Unity, tetapi checkout ini
adalah game Python/Pygame. Spesifikasi Unity dipetakan ke modul `src/nur_game/`
dan JSON netral di `assets/content/`.

**Alasan:** Tidak ada tooling Unity di checkout dan tidak ada proyek Unity nyata.
Membuat placeholder `.prefab`/`.cs` hanya akan menghasilkan file yang tidak bisa
dijalankan atau diverifikasi. Pemetaan penuh ada di `assets/content/README.md`
dan `05-specifications.md`.

## D2 — v4 berdiri sendiri, v3 tidak diubah

**Keputusan:** `src/nur_game/engine/` dan `geometry.py` memuat controller Pymunk
milik NUR. Paket game lain, tes, dan asetnya dihapus dari v4 saja. Folder `v3`
tidak disentuh.

**Keputusan terkait:** modul dengan banyak tanggung jawab dipecah menjadi paket
(`engine/`, `game/`, `puzzles/`, `art/`, `audio/`, `spawn_manager/`, `sanity/`,
`hallucinations/`); berkas data atau satu fungsi kohesif tetap utuh. Nama publik
tidak berubah, sehingga pemanggil lama tetap bekerja.

**Alasan:** v4 adalah revisi setelah evaluasi visual/gameplay; percobaan
mencampur dua controller hanya menimbulkan regresi dan duplikasi nama.

## D3 — Dunia kontinu, bukan ruang terpisah

**Keputusan:** 29 wilayah disatukan menjadi dunia 112.360 px dalam satu Pymunk
space. Pergantian wilayah hanya mengubah alamat naratif.

**Alasan:** Memuat ulang ruang memutus identitas peti, gerbang, dan puzzle saat
pemain mundur. Satu space membuat checkpoint dan backtracking konsisten.

## D4 — Penomoran lapisan depan ke belakang

**Keputusan:** Lapisan 1 foreground, 2 gameplay, 3 objek kecil, 4 latar jauh;
penggambaran dilakukan dari belakang ke depan.

**Alasan:** Mengikuti cara pengguna menyebut kedalaman, bukan urutan kode.
Dokumentasi dan `scenery.py` memakai konvensi yang sama untuk menghindari
terbaliknya parallax.

## D5 — Lentera melindungi dari monster, bukan dari mesin

**Keputusan:** Selama lentera dibawa, monster tidak menyerang—termasuk pada
charge nol. Mesin (presser, duri, uap, balok, pendulum, gergaji) dan jatuh tetap
mematikan.

**Alasan:** Cahaya adalah komitmen dan pesan harapan, bukan indikator darah.
Pemisahan ini membuat risiko monster muncul hanya setelah pemain meletakkan
lentera, sementara bahaya lingkungan tetap menuntut keterampilan.

## D6 — Generator sebagai sumber kebenaran konten

**Keputusan:** Tabel di `src/scripts/generate_content.py` menghasilkan semua JSON
prefab, `puzzle_index.md`, dan library index. File hasil generasi tidak disunting
langsung.

**Alasan:** 33 platform, 32 obstacle, dan 26 puzzle mudah menjadi tidak konsisten
bila diedit satu per satu. Generator membuat regenerasi deterministik dan
validator bisa memeriksa duplikat nama serta batas tuning.

## D7 — Validator membaca registry F4 yang sebenarnya

**Keputusan:** `src/scripts/validate_content.py` mengimpor
`nur_game.puzzles.COMPONENT_CLASSES` sebagai allowlist, dengan fallback statis
bila dijalankan mandiri. Tes juga membangun setiap spec lewat
`PuzzleManager.generate_from_spec()`.

**Alasan:** Allowlist yang ditulis dua kali akan meleset ketika komponen F4
berubah. Menguji generasi runtime membuktikan katalog dan implementasi benar-benar
sejalan, bukan sekadar cocok secara tekstual.

## D8 — Tes dipisah menjadi `tests/nur/` dan `tests/v4/`

**Keputusan:** Dua folder tes dengan fixture `game` berbeda dipertahankan;
`pytest.ini` memakai `pythonpath = src` dan `testpaths = tests`.

**Alasan:** `tests/nur` menguji kontrak room-based lama lewat `baseline_game`,
sedangkan `tests/v4` menguji controller kontinu. Menggabungkan keduanya akan
membuat fixture saling menimpa dan menyembunyikan regresi.

## D9 — Tidak ada operasi git

**Keputusan:** Semua pekerjaan ditulis langsung ke working tree. Tidak ada
klaim commit, branch, atau PR.

**Alasan:** Tidak ada repository git pada checkout. Membuat repo baru tanpa
permintaan akan mengubah cara pengguna mengelola proyek.

## D10 — Struktur folder sesuai permintaan

**Keputusan:** Root hanya berisi `assets/`, `docs/`, `src/`, `tests/` (ditambah
file konfigurasi/venv). Kode masuk `src/`, data masuk `assets/content/`, bukti
verifikasi masuk `docs/verification/`.

**Alasan:** Memisahkan kode, data, dokumentasi, dan pengujian membuat path
pendek dan peran tiap folder jelas. Catatan status tim (`PROJECT-STATUS.md`) dan
rincian task (`06-planning.md`) dipindah ke `docs/` agar tidak ada folder
`tasks/` yang berdiri sendiri.
