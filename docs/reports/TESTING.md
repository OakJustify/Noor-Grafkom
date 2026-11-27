# Laporan Testing

Tanggal: 27 November 2026

## Perintah
- `python -m pytest -q`
- `ruff check .`
- smoke test level 16 segmen
- smoke test loop game dengan event sintetis

## Temuan dan perbaikan
1. Exit level tidak melakukan apa pun. Diperbaiki: pemain sekarang pindah ke level berikutnya sesuai rantai Prolog → S1 → S2 → S3 → S4 → ending.
2. Fragmen bisa diambil berulang kali. Diperbaiki: ID fragmen dicatat dan tidak bisa diambil lagi.
3. Belum ada checkpoint aktif/respawn. Diperbaiki: checkpoint aktif saat didekati dan dipakai untuk respawn saat jatuh.
4. Belum ada layar ending/edukasi/kredit. Ditambahkan scene sederhana agar game bisa selesai.
5. Overlay jeda menutupi layar sepenuhnya. Diperbaiki memakai surface transparan.

## Catatan
Folder `docs/reports/` sebelumnya kosong, jadi tidak ada laporan bug lama yang bisa dibaca.
