# Noor — cerita, cutscene, dan ending

Dokumen produksi ini mengandung spoiler. Adaptasi menggunakan naskah
`Noor - Naskah Cerita - Draf 1.txt` yang dibuat untuk tim; detail tokoh dan dialog
berasal dari draf tersebut. Cerita ditampilkan sebagai subtitle Indonesia,
bukan voice acting atau dubbing.

## Perjalanan pemain

1. CS00 membuka jalan berwarna dan memberi petunjuk sederhana, tanpa diagnosis.
2. Pemain berjalan, merawat lentera, dan menyelesaikan puzzle yang sudah ada.
3. Enam benda di rute utama memicu CS01–CS06. Jika diperoleh tidak berurutan,
   cutscene menunggu pendahulunya; adegan tidak membocorkan akhir lebih dahulu.
4. Warna memudar setelah masing-masing memori selesai atau dilewati. Mengisi
   lentera tidak mengembalikan warna cerita; baterai dan pemudaran adalah dua
   sistem berbeda. Benda cerita juga berbeda dari pita bahan bakar di lookout.
5. Ujung jalan hanya memicu CS07 setelah keenam benda dan memorinya lengkap.
   CS07 berlangsung 12 detik; tiga detik terakhir hitam penuh, tanpa HUD/subtitle.
6. CS08 menunjukkan Nur tua dan Dara dewasa di rumah nyata. Nur kesulitan
   mengenali anaknya; Dara memilih duduk dan menemani. Tidak ada penyembuhan
   ajaib atau pertarungan untuk mengalahkan penyakit.
7. Tiga kartu penutup baru menyebut Alzheimer dan menjelaskan bahwa dunia
   simbolis/kisah fiksi ini tidak mewakili pengalaman semua orang.

## Adegan dan pemicu

Indeks wilayah pada tabel mengikuti `REGIONS` (mulai dari 0). Benda berada
100 px di depan stasiun sumbu wilayah tersebut, pada jalur bawah yang dapat
berjalan kembali. Atlas menandai benda yang belum ditemukan.

| Benda | Indeks wilayah | Adegan | Durasi |
|---|---:|---|---:|
| — | Awal permainan | CS00: Jalan yang terang | 15 detik |
| F01: Pita merah | 1 | CS01: Simpul yang miring | 25 detik |
| F02: Cangkir biru | 5 | CS02: Cangkir di sebelah kanan | 30 detik |
| F03: Kunci kecil | 10 | CS03: Jalan yang biasanya | 35 detik |
| F04: Foto terlipat | 15 | CS04: Foto di depan rumah | 35 detik |
| F05: Catatan dapur | 20 | CS05: Resep yang dibaca lagi | 40 detik |
| F06: Kain bersulam | 25 | CS06: Nama pada kain | 40 detik |
| Semua memori selesai | Ujung jalan terakhir | CS07: Ujung jalan | 12 detik |
| CS07 selesai | Otomatis | CS08: Di sebelah kanan meja | 90 detik |

## Kontrol dan checkpoint

- Cutscene: **Enter** maju satu subtitle/shot, **Space** jeda, **Esc** lewati.
- Gameplay: **K** membuka galeri fragmen; **J** membuka atlas/jurnal.
- Galeri: **↑/↓** pilih, **Enter** putar adegan terbuka, **K/Esc** kembali.
- Penutup: **Enter** kartu berikutnya, **K** galeri, **R** perjalanan baru,
  **Esc** menu. Adegan terakhir dapat diputar kembali dari galeri.
- **M** mute/unmute musik dan ambience nonverbal; tidak ada suara yang membaca
  dialog. Void dibisukan tanpa mengubah pilihan mute pemain.
- Simulasi fisika, mesin, drain lentera, stamina, sanity, serta waktu gameplay
  berhenti selama cutscene dan galeri. Replay tidak menambah benda atau progres.
- Save v4 menyertakan inventaris cerita, adegan selesai/aktif, dan status akhir.
  Melanjutkan cutscene mengulang adegan aktif dari awal, bukan kehilangan fragmen.
- Save lama tanpa data cerita dimigrasikan dengan membuka benda yang sudah
  dilewati; memorinya diputar berurutan agar pemain tidak dipaksa mengulang jalan.
  Checkpoint tidak valid ditolak; keluar dari menu atau gagal `--continue` tidak
  menimpa file checkpoint yang ada.

## Implementasi grafika

Mode latihan developer: jalankan `src/play_nur.py --dev`, lalu **F1–F6** untuk
teleport dekat benda F01–F06. `--dev --fragment F04` langsung menuju foto.
Berjalan ke kanan memicu koleksi/cutscene normal. Teleport menyiapkan memori
pendahulu, mengosongkan tujuan dan memori berikutnya, serta memulihkan
lentera/stamina tanpa mengganti physics space. Seluruh save sesi developer
dinonaktifkan; `--continue` tidak bisa digabung dengan `--dev`.

**F7** memulai urutan finale CS07 → CS08 → kartu penutup, **F8** langsung CS08,
dan **F9** langsung kartu penutup. Semua memori disiapkan, fisika tetap sama,
dan save tetap nonaktif. CLI: `--dev --ending` (default void), `--dev --ending
realworld`, atau `--dev --ending cards`. Opsi ini tidak bisa digabung dengan
`--fragment`. Preview void tetap hitam murni dan sunyi; audio nonverbal kembali
saat CS08 sesuai pilihan mute pemain.

Bukti awal mode developer ada di `verification/developer/`: keenam tujuan diuji
dengan tombol, gerakan biasa, dan capture cutscene; launcher normal tetap
memulai CS00. Bukti ending ada di `verification/developer-endings/`:
F7/F8/F9, ketiga opsi launcher, pixel void, dan suite penuh. Suite ending
lulus 412 tes, termasuk 26 tes teleport fragmen dan 17 tes preview ending.

Menu biasa (`--menu`, tanpa `--dev`) memiliki tombol **MODE DEVELOPER** dan
shortcut **D**. Sesi latihan baru mulai dekat F01; save dimatikan sebelum
memulai. Input klik mengikuti skala jendela. Kembali ke menu dari kartu
penutup lalu Enter/C mengembalikan pilihan save perjalanan normal; gagal
continue tidak boleh menulis progres latihan. Bukti ada di
`verification/developer-menu/`: suite terbaru lulus 428 tes, termasuk 16 tes
tombol/menu, serta capture launcher dan tiga ukuran jendela.

- `cinematics/catalog.py`: data adegan/cue/subtitle dan kartu penutup.
- `cinematics/fragments.py`: enam benda dan koordinat dunia pada rute utama.
- `cinematics/progress.py`: clock, antrean, gate akhir, replay, dan validasi cerita.
- `cinematics/renderer.py`: ilustrasi vektor original dengan `Ink`/Pygame:
  manusia, tangan, rumah, furnitur, cangkir retak, pita miring, foto, resep, dan
  sulaman DARA. Ada pan/zoom kecil, uap teh, dan gerakan tangan yang dicache.
- `game/controller.py`: pemicu koleksi, input cutscene, pembekuan gameplay,
  dan penggantian finale lama pada launcher aktif.
- `game/presentation.py`: subtitle tanpa HUD bocor, galeri, peta fragmen,
  desaturasi/penggelapan berdasarkan cerita, dan kartu ending dunia nyata.
- `game/persistence.py`: serialization cerita dan restore checkpoint.

Paths/bentuk kompleks, pewarnaan, transformasi, teks, dan interaksi visual
menggunakan komposisi CPU Pygame. Ini bukan shader GPU atau animasi studio.
`LocalFinale` lama hanya dipertahankan untuk regresi mekanik internal dengan
`cinematics=False`; launcher normal memakai cerita baru. Eksplorasi tetap tanpa
NPC AI, tetapi cutscene memiliki ilustrasi manusia Nur dan Dara.

## Verifikasi yang dapat dijalankan

Windows, dari root checkout:

```powershell
.venv-nur\Scripts\python.exe src\play_nur.py --menu
.venv-nur\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = 'src'
.venv-nur\Scripts\python.exe src\scripts\playtest_continuum.py --output docs\verification\story\campaign.json --captures docs\verification\story\captures
```

Pilot memakai input berjalan/lompat/interaksi biasa dan menunggu cutscene sesuai
clock-nya. Report memisahkan waktu gameplay dan cutscene serta mencatat urutan
adegan, subtitle/shot yang benar-benar dilalui, dan identitas satu physics space.
Tes unit yang menempatkan pemain pada koordinat tertentu hanya memverifikasi
boundary; bukan bukti kampanye berbasis input. Tes pixel/layout dan capture tidak
menggantikan playtest manusia, aksesibilitas, pacing, atau validasi medis.

Hasil kampanye launcher-default yang terekam pada implementasi ini:

- `verification/story/campaign.json`: selesai, 144 milestone, satu physics space,
  urutan CS00 → CS08, 1199.908 detik gameplay dan 322 detik cutscene.
- `verification/story/captures/`: 71 cue/shot direkam dari rute input sebenarnya;
  seluruh subtitle dan identitas cue dicocokkan dengan katalog. Frame
  `CS07-cue-04.png` diverifikasi memiliki semua piksel RGB nol.
- Hash sumber pada report dicocokkan kembali dengan kode saat verifikasi.
- `verification/story/pytest.xml`: 344 tes lulus, tanpa failure/error/skip;
  jumlah testcase dicocokkan dengan total pada XML.
- Launcher normal diuji 120 frame tanpa save; launcher menu juga diuji. Keduanya
  selesai tanpa error dan report memakai hash sumber yang sama dengan kampanye.

Batas pemeriksaan visual: API inspeksi gambar mengembalikan HTTP 401. Dua
reviewer alternatif juga hanya menerima path, bukan piksel yang dapat dilihat.
PNG dapat didekode dan tes render/layout lulus, tetapi komposisi, penampilan
tokoh, keterbacaan visual, dan kualitas artistik belum mendapat review visual
manual. Buka capture untuk tinjauan tim; keberhasilan capture bukan persetujuan
visual atau validasi medis.

## Revisi ilustrasi karakter

- `cinematics/portraits.py` mengganti template manusia geometris dengan kontur
  Bézier tertutup: kepala/leher, pakaian, lengan melengkung, dan telapak kompak.
  Nur muda/tua dan Dara kecil/dewasa memakai rambut dan proporsi berbeda.
- Painter dipakai renderer utama, foto keluarga, dan benda fragmen. Tokoh
  saling menghadap; pose mengikat pita menjangkau rambut anak. Cangkir, kain,
  serta pita mengikuti koordinat tangan/kepala. Framing keluarga diperbaiki
  agar kepala tidak terpotong; posisi anak mengikuti tinggi tubuh barunya.
- Naskah, subtitle, durasi, save, dan mekanik gameplay tidak diubah oleh revisi.
- Bukti lama tetap di `verification/story-art/before/`; hasil baru berada di
  `verification/story-art/after/`. `verification/story-art/before-after.png`
  membandingkan sembilan pasangan frame kampanye yang sama.
- Verifikasi baru: 369 tes lulus; 71 cue kampanye sesuai katalog, urutan CS00
  sampai CS08 lengkap, 144 milestone, satu physics space, 1199.908 detik
  gameplay dan 322 detik cutscene. Void RGB nol, tiga kartu penutup, serta
  launcher normal/menu diuji; hash sumber dicocokkan dengan hasil kampanye.
- Pemeriksaan visual tetap diblokir HTTP 401. Tes geometri/piksel memastikan
  batas, koneksi, perbedaan proporsi, dan rendering; bukan persetujuan artistik.
