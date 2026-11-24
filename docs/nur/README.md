# NÜR — campaign perjalanan pulang

> Pengembangan Game Petualangan 2D Sederhana Berbasis Grafika Komputer dengan
> Vector Art, Parallax, dan Efek Pencahayaan sebagai Media Penyampaian Pesan
> Harapan di Tengah Kegelapan.

NÜR adalah rombakan konseptual `v3` dari ECHO. Kode lama `echo_game/` sengaja
dibiarkan utuh sebagai baseline regresi; semua permainan baru tinggal di
`nur_game/`. Perubahan ini **hanya** menyentuh `v3/`.

## Menjalankan

```bash
# dari folder v3
.venv-echo/bin/python play_nur.py

# smoke test deterministik tanpa jendela
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
PYTHONPATH=/tmp/opencode/pydeps:. \
.venv-echo/bin/python play_nur.py --headless --frames 5 --no-save \
  --report /tmp/opencode/nur-report.json

# test NÜR
PYTHONPATH=/tmp/opencode/pydeps:. \
.venv-echo/bin/python -m pytest -q tests_nur
```

Kontrol: `A/D` atau `←/→` berjalan, `SPACE/W/↑` lompat, `E` berinteraksi,
`ESC` jeda, `R` mengulang ruangan, `M` bisu. Tahan `E` untuk menarik krate
atau memegang tali; `W/S` memanjat, `Space` melepas tali. Tidak ada tutorial
modal; label kontekstual hanya muncul dekat objek interaktif.
`J` membuka jurnal dan peta, `←/→` mengganti halaman. Jurnal menjeda simulasi
dan pengurangan cahaya. Tekan-lepas `E` memilih tombol/saklar/nada yang paling
dekat, berbeda dari tahan `E` untuk menarik krate. `C` di menu atau
`play_nur.py --continue` melanjutkan checkpoint.

## Struktur campaign

| Modul | Isi |
|---|---|
| `nur_game/config.py` | palet muted, konstanta cahaya, jalur aset |
| `nur_game/story.py` | fragmen memori, caption mengganggu, naskah cutscene statis |
| `nur_game/state.py` | `Lantern`, `Memory`, `Narrative` berbasis RNG ter-seed |
| `nur_game/levels.py` | 29 ruangan: 4 pembuka → 24 bab perjalanan → boss |
| `nur_game/journey.py` | empat babak baru, layout dan teks puzzle/story |
| `nur_game/quests.py` | 6 keluarga puzzle, interaksi lokal, state checkpoint |
| `nur_game/environments.py` | 10 gaya environment baru dengan parallax |
| `nur_game/threats.py` | bayangan yang mundur dari lentera, telegraf hanya tanpa lentera |
| `nur_game/boss.py` | "Yang Menyebut Nama": gema + berhenti menjawab |
| `nur_game/art.py` | parallax, material kayu/logam, cahaya lembut, pintu keluar |
| `nur_game/illustration.py` | aset vector supersampled yang di-cache, atlas animasi |
| `nur_game/wisp.py` | karakter wisp berjubah, 4 animasi × 8 frame dan playback |
| `nur_game/generate_wisp.py` | export 4 sprite sheet PNG transparan + manifest |
| `nur_game/physics.py` | aturan fairness NÜR tanpa mengubah physics ECHO |
| `nur_game/audio.py` | 3 bed CC0 + foley procedural milik sendiri |
| `nur_game/game.py` | loop aplikasi, HUD diegetik, ending 4 frame |
| `nur_game/generate_assets.py` | generator deterministik gambar akhir & WAV |

## Sistem utama

### Lilin sebagai otak

Kapasitas lilin **hanya turun**: `1.00 → 0.75 → 0.50 → 0.25 → 0`.
Mengambil fragmen memori mengurangi kapasitas seperempat secara permanen;
waktu juga menggerus muatan secara linear. Kematian mengurangi muatan, bukan
kapasitas. Tidak ada item yang mengembalikan cahaya ke 100%.
Drain waktu sekarang 0,00028 per detik, disesuaikan untuk campaign panjang;
fragmen tersebar di rumah, arsip, hutan, dan babak perawatan, bukan habis di
empat ruangan pembuka.

`Lilin ingatan` di dapur memperbaiki satu fragmen yang salah (makna), bukan
lilin (penglihatan). Ini menjawab permintaan item pengembalimemory tanpa
melanggar aturan cahaya.
Jika lilin diambil sebelum fragmen salah ditemukan, efeknya disimpan sampai
fragmen tersebut diambil. Pickup tetap satu kali per run, termasuk setelah retry.

### Fragment & ketidakpercayaan

Empat fragmen: foto, label kunci, resep, surat. Dua di antaranya salah dan
tampak identik; perbedaannya hanya lewat kontradiksi detail (jam 14.00 vs
04.00, gula vs garam). Caption di luar konteks muncul dengan RNG ter-seed;
tiga baris anchor selalu muncul berurutan, termasuk:

- `sepertinya kamu lupa menutup pintu`
- `kau membunuhku!`

Teks yang menentukan mekanik puzzle **tidak pernah** berubah.

### Ancaman & puzzle

**Membawa lentera selalu melindungi dari monster**, termasuk pada muatan nol.
`Lantern.carried` terpisah dari `charge`: cahaya mengatur penglihatan, bukan
hak monster untuk menyerang. Serangan yang sudah berjalan langsung dibatalkan;
bayangan mundur dan memudar, boss tidak menembakkan proyektil. Tidak ada tombol
untuk membuang lentera dalam campaign saat ini. Jalur serangan tanpa lentera
tetap ada sebagai perilaku eksplisit dan diuji terpisah.

Rumah memperkenalkan rak memori dan krate. Koridor memiliki rute rak bertingkat
di atas gergaji yang gerakannya periodik. Dapur memakai krate + pelat + pintu:
tahan `E` untuk menarik, tinggalkan krate di pelat, ikuti kabel menuju pintu.
Pintu tertutup menghalangi, bukan membunuh lewat proximity. Lilin ingatan harus
diambil dengan `E` dari dekat; hanya sekali per run, termasuk setelah retry.
Loteng mempunyai celah 220 px dengan tali fisik untuk berayun, lalu rak di atas
gergaji. Bayangan bertambah seiring waktu tetapi tidak menghalangi traversal.

Gergaji dan jatuh ke jurang **tetap berbahaya**: perlindungan monster bukan
invulnerability terhadap mesin atau lingkungan. Retry tidak mengisi ulang
cahaya, termasuk ketika muatan sudah nol.

### Empat babak perjalanan baru

1. **Desa**: kebun, sumur, menara lonceng, bengkel, rumah kaca, peron.
2. **Arsip**: kelas, arsip hujan, perpustakaan suara, gudang surat, observatorium, ruang sambung.
3. **Hutan**: penanda jalan, kincir, kapel, jembatan timbang, danau, lentera hutan.
4. **Perawatan**: halaman, air hangat, musik, lemari kenangan, jendela, ambang pulang.

Setiap bab mempunyai tiga catatan dan tiga perangkat. Enam keluarga puzzle
dipakai kembali pada tiap babak, dengan layout, jawaban dan narasi berbeda:

- **Komponen lentera:** cocokkan label yang ditemukan dengan salah satu dari
  empat slot fisik; memilih slot salah tidak membuka jalan.
- **Debit air:** buka/tutup cabang bernilai 1/2/4 sampai jumlah sesuai catatan;
  tangki indikator menunjukkan jumlah aliran, bukan simulasi fluida baru.
- **Melodi:** mainkan urutan 3–6 nada lewat empat tombol berbeda. Nada salah
  mereset melodi saja. Nada visual tetap terbaca saat mute.
- **Neraca:** dorong tiga krate nyata ke pelat pasangan; posisi tubuh pemain
  tidak bisa menggantikan krate.
- **Cermin:** putar arah pantulan mengikuti peta yang ditemukan. Garis cahaya
  memperlihatkan arah; ini puzzle orientasi, bukan ray-tracer fisik.
- **Rangkaian:** cocokkan tiga saklar terpisah dengan pola kiri/tengah/kanan.

Reparasi memakai perjalanan ambil/antar; musik dan cermin mengumpulkan semua
catatan sebelum mengoperasikan perangkat. Jurnal menyimpan petunjuk, HUD
menunjukkan tujuan dan arah. Tidak ada time-lock, delay wajib membaca atau
monster yang sengaja ditingkatkan damagenya untuk memanjangkan game.

Puzzle selesai melatch progress dan membuka pintu. Retry mempertahankan
progress, kembali ke stasiun yang terakhir selesai, dan tidak mengisi ulang
lentera. Save version 2 menyimpan puzzle, jurnal, memori, status lilin dan waktu
main; save lama pada arena #5 dimigrasikan ke boss terakhir yang baru (#29).
Posisi krate yang belum dikonfirmasi dan kemajuan fase boss di-reset saat resume;
ini checkpoint campaign, bukan save physics frame-by-frame.

### Boss akhir

Boss tidak menambah kontrol baru. Fase 1: kumpulkan tiga gema ingatan melalui
rak bertingkat yang bisa dicapai dari lantai. Lentera menahan serpihan boss;
serpihan hanya aktif jika lentera secara eksplisit tidak dibawa. Fase 2: boss
mengulang nama; pemain menekan `E` dekat boss
tiga kali untuk **berhenti menyebut nama** — analogi `MERCY` Undertale.
Fase 3: keruntuhan dan cutscene statis 4 frame.

Mencapai tepi kanan arena tidak lagi memicu `complete` campaign dan membekukan
gerakan sebelum boss selesai. Ending hanya dipicu oleh fase mercy.

### Artwork & verifikasi

Semua aset gameplay baru adalah vector art orisinal yang dibuat lokal,
di-antialias pada resolusi 2× lalu di-cache: karakter idle/jalan/udara, tiga
siluet bayangan, boss berjubah, krate, kertas memori, dan lilin. Tidak ada
download aset, service eksternal, atau dependency baru. Ruangan diberi panel
kayu, buku, bingkai, kaca, tirai, botol, peralatan dapur dan tekstur plaster.
Cahaya radial/vignette memakai alpha falloff halus, bukan additive RGB yang
membuat lingkaran putih. Cache cahaya dibatasi 16 surface.

`tests_nur/` mencakup perlindungan pada semua brightness, pembatalan lunge,
boss tanpa serangan, pickup satu kali, kontrol tarik/panjat, material/render,
serta traversal input-only pembuka dan boss sampai ending pada muatan nol.
Suite sekarang juga memeriksa seluruh 24 bab baru pada muatan nol, durasi
campaign penuh, save/resume, jurnal, input salah dan gate yang belum selesai.
Cache background dibatasi 6 ruangan, cache cahaya 16 surface.
Analisis playtest dan screenshot aktual:
[`verification/PLAYTEST.md`](verification/PLAYTEST.md).

### Karakter wisp berjubah

Player sekarang adalah wisp: wajah bercahaya di dalam tudung kosong, jubah
bergerak, ekor spirit tanpa kaki, dan lentera kuningan yang tetap dibawa.
Empat set terpisah mempunyai **8 frame per aksi (32 total)**:

- Idle: 7 fps, melayang lembut, nyala wajah dan kain/ayunan lentera bergerak.
- Walk: 10 fps, glide pelan dengan gelombang kain pendek.
- Run: 16 fps, condong ke depan dengan jubah/scarf yang memanjang ke belakang.
- Jump: takeoff, naik, apex, turun dan landing mengikuti kecepatan vertikal;
  tidak berputar ulang saat masih di udara.

Setiap frame berukuran 104×104 dengan pivot tetap. Gameplay tidak diubah:
walk dipakai saat bergerak pelan/menarik krate, run pada kecepatan jalan penuh,
tanpa tombol sprint baru. Animasi berhenti saat pause dan reset saat retry.

Sprite sheet transparan, manifest dan preview ada di
[`assets/nur/sprites/wisp/`](../../assets/nur/sprites/wisp/README.md).
Regenerasi: `.venv-echo/bin/python -m nur_game.generate_wisp` dari `v3`.
Renderer menggunakan frame vector cache yang sama persis dengan hasil export;
PNG adalah export untuk diperiksa/dipakai ulang, bukan sumber art terpisah.

## Prinsip desain yang dipakai

Hasil riset Undertale + Limbo diterjemahkan menjadi aturan konkret:

1. Mekanik adalah cerita — lilin adalah jam dan penglihatan; perlindungan tidak hilang saat cahaya menyusut.
2. Kematian adalah diagnosis: efek 1 detik + audio, bukan skor atau "Game Over".
3. Jalur benar mahal: memperbaiki ingatan tidak mengembalikan penglihatan.
4. Learned, not told: rumah hanya berisi benda yang bisa dipegang/didorong.
5. Monster punya satu motif dua nada; pengenalan lebih penting daripada pertarungan.
6. Saat tanpa lentera: telegraf 0,8–1,2 detik, maksimal 6 proyektil; campaign selalu membawa lentera.
7. Bayangan mundur dan memudar dekat pemain sehingga status perlindungan terbaca.
8. Parallax tiga lapis dipakai untuk menyembunyikan informasi, bukan sekadar dekorasi.
9. Sunyi adalah default; musik/ambience masuk sebagai pengingat, bukan penunjuk emosi.
10. Satu motif, lima degradasi — bukan lima lagu.
11. Humor hangat di awal tidak dipaksakan; objek yang sama kembali dengan satu frame berbeda di akhir.
12. Guardrail etis: Alzheimer tidak disamakan dengan "monster jahat"; ancaman berasal dari ketidakpastian pengalaman subjektif.

## Audio open source

Tiga bed ambience diunduh dari Freesound dengan filter lisensi **CC0** dan
halaman tiap sound déjà diverifikasi. Detail + URL permanen ada di
`assets/nur/CREDITS.md`. Foley pendek dibuat sendiri dan dirilis CC0.
Tidak ada audio dari OST Undertale/Limbo yang dipakai.

## Status

Campaign 29 ruangan dapat dimainkan dari `RUMAH` sampai ending statis.
Run otomatis input-only dengan jawaban diketahui memerlukan **19:28 waktu game**;
ini bukan klaim 19 menit playtest manusia atau jaminan semua pemain menikmati
durasi yang sama. Keenam keluarga puzzle sengaja dipakai ulang; feedback manusia
tentang repetisi, keterbacaan petunjuk dan pacing masih perlu dikumpulkan.
Renderer NÜR tidak membutuhkan aset gameplay ECHO; baseline ECHO dipertahankan.
