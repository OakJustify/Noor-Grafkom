# NÜR — vertical slice

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
  --report /tmp/nur-report.json

# test NÜR
PYTHONPATH=/tmp/opencode/pydeps:. \
.venv-echo/bin/python -m pytest -q tests_nur
```

Kontrol: `A/D` atau `←/→` berjalan, `SPACE/W/↑` lompat, `E` berinteraksi,
`ESC` jeda, `R` mengulang ruangan, `M` bisu. Tidak ada tutorial dan tidak ada
dialog instruksi di dalam ruangan pertama.

## Struktur vertical slice

| Modul | Isi |
|---|---|
| `nur_game/config.py` | palet hampir monokrom, konstanta cahaya, jalur aset |
| `nur_game/story.py` | fragmen memori, caption mengganggu, naskah cutscene statis |
| `nur_game/state.py` | `Lantern`, `Memory`, `Narrative` berbasis RNG ter-seed |
| `nur_game/levels.py` | 5 ruangan: Rumah → Koridor → Dapur → Loteng → boss |
| `nur_game/threats.py` | ancaman world-space dengan telegraf 1 detik |
| `nur_game/boss.py` | "Yang Menyebut Nama": dodge + berhenti menjawab |
| `nur_game/art.py` | parallax siluet, vignette, grain, radial candle light |
| `nur_game/audio.py` | 3 bed CC0 + foley procedural milik sendiri |
| `nur_game/game.py` | loop aplikasi, HUD diegetik, ending 4 frame |
| `nur_game/generate_assets.py` | generator deterministik gambar akhir & WAV |

## Sistem utama

### Lilin sebagai otak

Kapasitas lilin **hanya turun**: `1.00 → 0.75 → 0.50 → 0.25 → 0`.
Mengambil fragmen memori mengurangi kapasitas seperempat secara permanen;
waktu juga menggerus muatan secara linear. Kematian mengurangi muatan, bukan
kapasitas. Tidak ada item yang mengembalikan cahaya ke 100%.

`Lilin ingatan` di dapur memperbaiki satu fragmen yang salah (makna), bukan
lilin (penglihatan). Ini menjawab permintaan item pengembalimemory tanpa
melanggar aturan cahaya.

### Fragment & ketidakpercayaan

Empat fragmen: foto, label kunci, resep, surat. Dua di antaranya salah dan
tampak identik; perbedaannya hanya lewat kontradiksi detail (jam 14.00 vs
04.00, gula vs garam). Caption di luar konteks muncul dengan RNG ter-seed;
tiga baris anchor selalu muncul berurutan, termasuk:

- `sepertinya kamu lupa menutup pintu`
- `kau membunuhku!`

Teks yang menentukan mekanik puzzle **tidak pernah** berubah.

### Ancaman & puzzle

Koridor memperkenalkan gergaji bertelegraf dan satu bayangan. Dapur memakai
krate + pelat + pintu tanpa instruksi. Loteng menambah gergaji dan tiga
bayangan. Seiring waktu, direktur ancaman mengaktifkan lebih banyak entitas;
kompleksitas naik bersamaan dengan menyusutnya cahaya.

### Boss akhir

Boss tidak menambah kontrol baru. Fase 1: kumpulkan tiga gema ingatan sambil
menghindari serpihan yang telegrafnya jelas (1 detik) dan hitbox-nya lebih
kecil dari visual. Fase 2: boss mengulang nama; pemain menekan `E` dekat boss
tiga kali untuk **berhenti menyebut nama** — analogi `MERCY` Undertale.
Fase 3: keruntuhan dan cutscene statis 4 frame.

## Prinsip desain yang dipakai

Hasil riset Undertale + Limbo diterjemahkan menjadi aturan konkret:

1. Mekanik adalah cerita, bukan pelayan cerita — lilin sekaligus jam, health, dan "save file".
2. Kematian adalah diagnosis: efek 1 detik + audio, bukan skor atau "Game Over".
3. Jalur benar mahal: memperbaiki ingatan tidak mengembalikan penglihatan.
4. Learned, not told: rumah hanya berisi benda yang bisa dipegang/didorong.
5. Monster punya satu motif dua nada; pengenalan lebih penting daripada pertarungan.
6. Bullet heaven, bukan bullet hell: telegraf 0,8–1,2 detik, maksimal 6 proyektil.
7. Ancaman datang dari luar-frame: bayangan muncul di tepi cahaya, bukan di tengah.
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

Vertical slice sudah dapat dimainkan dari `RUMAH` sampai ending statis.
Yang belum diperluas: lebih banyak ruangan campaign, variasi archetype puzzle
turunan `rooms.py`, dan penggantian penuh aset lama `assets/echo/` — semuanya
sengaja ditunda sampai slice ini disetujui.
