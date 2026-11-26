# NOOR v4 · Yang masih di sini

Pengembangan terpisah dari `v3`: satu perjalanan panjang tentang ingatan,
cahaya yang dirawat, dan mesin yang masih bergerak. **Revisi setelah evaluasi
visual/gameplay; bukan klaim bahwa kualitas artistik sudah selesai.**

Adaptasi naskah cerita kini aktif: pembuka, enam cutscene memori, kehampaan
hitam, dan ending Nur–Dara di dunia nyata. Semua dialog berupa **subtitle
Indonesia tanpa dubbing**. Detail alur, kontrol, dan batas verifikasi ada di
[cerita/cutscene](docs/10-story-cinematics.md) (mengandung spoiler).

## Jalankan

Windows, dari root checkout:

```powershell
python main.py
```

`main.py` menambahkan `src/` ke `sys.path` sendiri, jadi bentuk ini bekerja
tanpa `PYTHONPATH` dan dari direktori mana pun. Semua opsi launcher tetap
tersedia:

```powershell
python main.py --menu              # menu utama
python main.py --continue          # lanjutkan checkpoint
python main.py --dev               # latihan developer, F1-F9
python main.py --dev --fragment F04
python main.py --dev --ending
```

Jika `python` belum menunjuk ke venv proyek, panggil interpreter-nya langsung:

```powershell
.venv-nur\Scripts\python.exe main.py --menu
```

Entry point alternatif yang setara: `src\play_nur.py` (butuh `src` di
`PYTHONPATH`, atau jalankan `pytest` yang sudah mengaturnya).

Jika membuat lingkungan baru:

```powershell
python -m venv .venv-nur
.venv-nur\Scripts\python.exe -m pip install -r requirements-nur.txt
.venv-nur\Scripts\python.exe main.py --menu
```

Linux/macOS memakai `.venv-nur/bin/python` sebagai pengganti path `Scripts`.

**C** di menu melanjutkan checkpoint; `--continue` juga tersedia.
Save v4 berada di `saves/nur-v4.json`, terpisah dari save v3.
`--no-save` menonaktifkan seluruh penulisan save.

### Developer mode: mencoba fragmen memori dan ending

Pada launcher menu biasa, klik **MODE DEVELOPER** atau tekan **D**:

```powershell
.\.venv-nur\Scripts\python.exe .\src\play_nur.py --menu
```

Tidak perlu flag `--dev`. Tombol memulai sesi latihan baru dekat fragmen F01;
save dinonaktifkan sebelum sesi dimulai. Setelah kembali ke menu dari kartu
penutup (Esc), Enter memulai perjalanan normal dan C melanjutkan checkpoint
normal; pilihan `--no-save` tetap dihormati.

```powershell
.venv-nur\Scripts\python.exe src\play_nur.py --dev
# Langsung dekat fragmen foto:
.venv-nur\Scripts\python.exe src\play_nur.py --dev --fragment F04
# Langsung mulai urutan void, dunia nyata, dan kartu penutup:
.venv-nur\Scripts\python.exe src\play_nur.py --dev --ending
```

Mode ini mulai dekat fragmen pertama. **F1–F6** memindahkan pemain ke depan
pita, cangkir, kunci, foto, catatan dapur, atau kain. Jalan sedikit ke kanan
untuk menyentuh benda dan memicu cutscene melalui mekanik koleksi biasa.
Shortcut juga bekerja saat cutscene, pause, galeri, atau menu.

**F7** langsung memulai void (CS07), lalu otomatis lanjut ke dunia nyata (CS08)
dan kartu penutup. **F8** melewati void dan mulai di dunia nyata; **F9** langsung
ke kartu penutup. Ketiganya menyiapkan enam memori dalam sesi latihan, tanpa
menulis checkpoint. Untuk memilih tahap saat launch, pakai `--dev --ending
realworld` atau `--dev --ending cards`. `--ending` dan `--fragment` tidak bisa
digabung. Enter/Space melanjutkan subtitle; Esc melewati satu adegan;
Enter/Space pada kartu penutup melanjutkan kartu berikutnya.

Setiap teleport menyiapkan memori sebelum tujuan dan mengosongkan tujuan serta
memori sesudahnya, sehingga benda yang sama bisa diuji berulang kali. Lentera
dan stamina diisi ulang; fisika tetap memakai dunia yang sama. Mode ini bukan
invincibility: rintangan tetap berbahaya. Save otomatis dinonaktifkan dan
`--dev` tidak bisa digabung dengan `--continue`; jalankan tanpa `--dev` untuk
kembali ke perjalanan/checkpoint normal.

## Kontrol

Saat pause (ESC) tersedia **ESC** kembali bermain, **R** kembali ke stasiun
terakhir, dan **B** simpan lalu kembali ke menu utama. Checkpoint tidak
dihapus: pilih **C** di menu untuk melanjutkan perjalanan yang sama, atau
**ENTER** untuk memulai perjalanan baru.

| Tombol | Fungsi |
|---|---|
| A/D atau ←/→ | Berjalan |
| Shift | Sprint 190 → 300 px/detik, menggunakan napas/stamina |
| Space / W / ↑ | Lompat; tahan saat turun untuk melayang setelah memakai stasiun sumbu |
| E / Ctrl | Rawat sumbu, mengingat jejak, mengambil pita, atau memegang peti/tali |
| W/S saat memegang tali | Naik/turun tali |
| Q | NYATA ↔ GAUNG: ubah persepsi dan platform yang benar-benar bisa diinjak |
| F (tahan) | Fokus cahaya: jangkauan bertambah, baterai lebih cepat berkurang |
| G | Letakkan lentera; tekan lagi di dekatnya untuk mengambil |
| E saat padam | Bara cadangan dan kembali ke stasiun terakhir |
| J | Atlas/jurnal; ←/→ mengganti halaman |
| K | Galeri fragmen; ↑/↓ pilih, Enter replay, K/Esc kembali |
| Enter / Space / Esc saat cutscene | Subtitle berikutnya / jeda / lewati satu adegan |
| M | Mute/unmute semua suara |
| Esc | Pause; R kembali ke tempat istirahat terakhir |

## Yang berubah dari v3

- **Dunia kontinu:** 29 wilayah, 112.360 px, terhubung dengan promenade terbuka.
  Pemain, peti, tali, puzzle, dan gerbang berada dalam satu Pymunk space.
  Melewati batas wilayah tidak memuat ulang ruang atau memindahkan pemain.
- **Empat lapisan, nomor depan ke belakang:** **1** foreground opak,
  **2** gameplay/interaksi, **3** hanya objek kecil (meja, kursi, pot, pohon kecil,
  batas 120 px), **4** rumah besar, bukit dan hutan jauh. Kamera masing-masing
  bergerak 1,12× / 1× / 0,82× / 0,12×. Objek ditambatkan ke posisi dunia;
  tidak ada cutout di sekitar pemain atau dissolve saat berganti wilayah.
- **Warna dan cahaya:** langit hangat, laut, viaduk, jendela, tanaman, partikel;
  desaturasi dan bayangan biru-ungu bertambah saat cahaya menipis.
  Saat charge nol, seluruh dunia hitam—hanya UI bantuan yang tetap terbaca.
- **Gerak:** enam set animasi delapan frame: idle, walk, run, jump, glide, focus.
- **Tanpa NPC eksplorasi:** stasiun sumbu tanpa penjaga memberi satu bara,
  napas baru, dan akses glide. Subtitle batin tidak membocorkan identitas awal.
  Nur dan Dara tampil sebagai manusia dalam ilustrasi cutscene.
- **Loop opsional:** naik ke lookout, ambil pita, bawa ke stasiun berikutnya
  untuk sedikit cahaya tambahan. Glide dibatasi stamina.
- **Mesin mematikan:** 28 rintangan di rute utama, bergiliran presser bertombol,
  duri, semburan uap, balok jatuh berkawat, dan pendulum. Ada tanda bahaya,
  peringatan dan jendela untuk menghindar; lentera tidak membuat besi aman.
- **Monster bertambah:** delapan bentuk berbeda, maksimum delapan calon per
  wilayah. Terbuka bertahap pada 20 / 90 / 180 / 300 / 420 / 570 / 720 / 900 detik
  atau ketika charge melewati ambang masing-masing. Mengisi cahaya tidak
  menghapus variasi yang sudah terbuka. Serangan didahului peringatan 1,2 detik.
- **Audio:** musik original, jump berpitch naik, landing lembut, dan lapisan
  stereo angin/dissonansi/napas sintetis yang berubah mengikuti cahaya.
- **Puzzles dipertahankan:** apparition/absence, parallax, witness, fold; 144
  milestone. Gerbang yang telah dibuka tetap terbuka untuk perjalanan balik.
- **Checkpoint v4:** posisi global, puzzle, persepsi, peti yang dipindah, perawatan,
  pita, stamina, letak lentera, inventaris cerita, dan progres akhir disimpan.
  Cutscene/galeri menghentikan simulasi dan drain; replay tidak menambah progres.
- **Pemudaran cerita:** terpisah dari charge lentera dan semakin kuat setiap
  memori selesai. Ending baru menggantikan pertarungan akhir pada launcher aktif.

### Aturan perlindungan lentera

**Monster tidak menyerang atau melukai NUR selama lentera dibawa, termasuk saat
charge nol.** Risiko serangan muncul setelah lentera diletakkan dan NUR keluar
dari jangkauan cahayanya. Presser, duri, uap, balok, pendulum, gergaji dan jatuh
tetap berbahaya. Pause dan jurnal menghentikan drain. Setiap stasiun memberi
kindling sekali; blackout memiliki jalan pemulihan tanpa menghapus puzzle.

## Konten & sistem hasil gabungan (O1–O3 + F1–F4)

Task dengan kontrak Unity dari `TASK_SPLIT_SPEC.md` diadaptasi ke checkout Python
ini; tidak ada proyek Unity tiruan di dalam repo.

- [Data konten](assets/content/README.md): 33 prefab platform, 32 prefab obstacle, dan
  26 spesifikasi puzzle sebagai JSON netral.
- [Status F1–F4](docs/PROJECT-STATUS.md): AI monster dan flee (`src/nur_game/monsters.py`,
  `src/nur_game/encounters.py`), spawn manager (`src/nur_game/spawn_manager/`),
  halusinasi/sanity (`src/nur_game/sanity/`, `src/nur_game/hallucinations/`), serta
  framework puzzle (`src/nur_game/puzzles/`, 22 komponen yang memetakan katalog puzzle).
  Paket F2–F4 memisahkan berkas per tanggung jawab; impor publik tetap
  `from nur_game.<nama> import ...`.
- [Penjelasan proyek](docs/01-overview.md), dengan arsitektur dan bukti verifikasi
  tetap berada di `docs/`.

```bash
# Regenerate data konten dari tabel sumber.
.venv-nur/bin/python src/scripts/generate_content.py

# Validasi O1-O3, termasuk kecocokan komponen dengan F4.
.venv-nur/bin/python src/scripts/validate_content.py
```

## Lihat dan verifikasi

- [Preview input nyata](docs/verification/captures/preview.png)
- [Arsitektur dan batas implementasi](docs/03-architecture.md)
- [Hasil, metode, dan bukti verifikasi](docs/07-testing.md)
- [Cerita dan bukti kampanye baru](docs/10-story-cinematics.md)
- [Kredit aset/audio](assets/nur/CREDITS.md)

```bash
# Tes controller v4, termasuk kampanye lengkap berbasis input.
.venv-nur/bin/python -m pytest -q

# Dua rute kampanye tanpa menulis save pemain.
PYTHONPATH=src .venv-nur/bin/python src/scripts/playtest_continuum.py --output docs/verification/campaign-sprint.json
PYTHONPATH=src .venv-nur/bin/python src/scripts/playtest_continuum.py --walk --output docs/verification/campaign-walk.json

# Capture berdasarkan input, bukan posisi/charge yang diatur untuk screenshot.
PYTHONPATH=src .venv-nur/bin/python src/scripts/capture_v4.py

# Smoke test launcher.
.venv-nur/bin/python src/play_nur.py --headless --frames 120 --no-save --mute --report docs/verification/smoke.json
```

## Batas kualitas

Spiritfarer digunakan sebagai **arah referensi** untuk kehangatan, gerak, warna,
dan kedalaman—bukan sebagai sumber karakter, aset, atau musik. Art masih vector
storybook prosedural, bukan hand-painted animation berkelas studio. Efek cahaya
adalah compositing/array CPU dengan Pygame, **bukan shader GPU**. Tidak ada NPC AI
eksplorasi, sistem hubungan, atau voice acting. Semua kode/aset game ECHO di v4 dihapus;
fisika yang dibutuhkan NUR sekarang berada di `src/nur_game/engine/`.

Panjang kampanye diuji oleh pilot yang mengetahui solusi, menggunakan input
biasa dan menunggu mesin ketika perlu. Bukti ini tidak menggantikan playtest manusia untuk keterbacaan,
aksesibilitas, pacing, daya tarik, atau penilaian suara melalui headphone.
Ini bukan simulasi medis, dan rekonsiliasi di akhir bukan penyembuhan ajaib.

`src/nur_game/baseline_game.py` dan `tests/nur/` menyimpan controller/kontrak room-based
sebelumnya untuk regresi; launcher hanya memakai controller kontinu v4.
Folder `v3` tidak diubah oleh pengembangan ini.
