# Dokumentasi NUR v4

Indeks seluruh dokumen. Tautan bersifat relatif terhadap folder `docs/`.

## Dokumen utama

| File | Isi |
|---|---|
| [01-overview.md](01-overview.md) | Identitas proyek, latar, tujuan, pengguna, ruang lingkup, dan kerangka OVR-001–045. |
| [02-requirement.md](02-requirement.md) | Kebutuhan fungsional dan non-fungsional yang harus dipenuhi. |
| [03-architecture.md](03-architecture.md) | Batas implementasi, dunia kontinu, lapisan kedalaman, dan modul inti. |
| [04-design.md](04-design.md) | Arah seni, palet, perilaku monster/mesin, dan rancangan puzzle. |
| [05-specifications.md](05-specifications.md) | Versi dependensi, parameter, format data, layer/tag, dan perintah validasi. |
| [06-planning.md](06-planning.md) | Rincian task F1–F4 dan urutan kerja yang disarankan. |
| [07-testing.md](07-testing.md) | Metode, hasil kampanye berbasis input, dan batas bukti. |
| [08-ai-guidelines.md](08-ai-guidelines.md) | Aturan menyunting kode, konten, dan dokumentasi untuk agen AI. |
| [09-decisions.md](09-decisions.md) | Keputusan arsitektur beserta alasannya. |
| [CHANGELOG.md](CHANGELOG.md) | Riwayat perubahan v4. |
| [PROJECT-STATUS.md](PROJECT-STATUS.md) | Status terkini task F1–F4. |

## Bukti verifikasi

- [verification/](verification/) — laporan kampanye, screenshot input nyata,
  audio, dan log pengujian. `campaign-sprint.json` dan `campaign-walk.json`
  adalah rute lengkap; `captures/` berisi cuplikan layar; `nur/` berisi hasil
  polish freebuff.
- Ringkasan dan batas interpretasi ada di [07-testing.md](07-testing.md).

## Di luar `docs/`

- [README.md](../README.md) — cara menjalankan, kontrol, dan batas kualitas.
- [assets/content/README.md](../assets/content/README.md) — pemetaan kontrak
  Unity ke JSON dan daftar pustaka konten O1–O3.
- [assets/nur/CREDITS.md](../assets/nur/CREDITS.md) — kredit aset dan audio.

## Konvensi

Nama file mengikuti pola `NN-topik.md`. Jangan membuat `docs/docs/` atau
placeholder kosong; isi dokumen baru dengan informasi yang benar-benar dipakai.
Bila memindahkan file, perbarui tautan di sini dan di dokumen lain yang
mereferensikannya.
