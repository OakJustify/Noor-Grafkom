# 04 — Rancangan visual dan gameplay

Dokumen ini menjelaskan *bagaimana* game terlihat dan terasa. Kebutuhan ada di
`02-requirement.md`, batas implementasi di `03-architecture.md`, dan parameter
teknis akhir di `05-specifications.md`.

## Arah seni

Noor memakai **ilustrasi vektor storybook prosedural**, bukan aset lukisan tangan
studio. Seluruh gambar utama digambar dengan `pycairo` (sesuai ketentuan mata
kuliah), lalu dikomposisikan dengan NumPy/Pygame di CPU. Tidak ada shader GPU
yang diklaim. Spiritfarer hanya dipakai sebagai arah referensi untuk kehangatan,
warna, gerak, dan kedalaman—bukan sumber karakter, aset, atau musik.

Palet hampir monokrom: `VOID (4,5,7)`, `INK (10,12,15)`, `ASH (25,27,32)`,
`SLATE (46,49,56)`, `BONE (168,160,146)`. Satu-satunya warna yang "dimiliki"
pemain adalah wax/ember lentera `(204,174,112)` / `(214,118,58)`. Merah gelap
`(76,18,26)` hanya muncul sebagai petunjuk tubuh, bukan tekstur darah.

Kedalaman visual berasal dari skala, kontras nilai, tumpang tindih, dan
parallax—bukan dari membuat objek transparan. Foreground gelap sengaja jarang
untuk menjaga ruang negatif. Interior padat dibuat opak; kontur antialias dan
ruang kosong tetap memiliki alpha.

## Empat lapisan, depan ke belakang

Penomoran mengikuti urutan visual pengguna, bukan urutan gambar kode.

| Lapisan | Isi | Pengali kamera |
|---|---|---:|
| 1 | Tiang dekat, dedaunan, kabel atas | 1,12 |
| 2 | Terrain, puzzle, mesin, peti/tali, pemain, monster, stasiun sumbu | 1 |
| 3 | Meja, kursi, pot, peti, pohon kecil; sambungan ≤120 px | 0,82 |
| 4 | Rumah besar, bukit, hutan jauh, air | 0,12 |

Gambar dijalankan terbalik (belakang ke depan). `scenery.py` menghasilkan chunk
960 px dengan identitas terikat pada koordinat dunia. Saat alamat wilayah
berubah, adegan tidak berganti, tidak fade, dan tidak menghapus foreground di
sekitar pemain.

## Cahaya sebagai sumber daya dan pesan

Lentera memiliki kapasitas yang turun per seperempat (`1,00 → 0,75 → 0,50 →
0,25 → 0`), dengan peluruhan `0,00028/detik` dan lantai `0,045`. Saat charge
nol, dunia yang dikomposisikan **hitam seluruhnya**; hanya instruksi pemulihan
UI yang tetap terbaca. Fokus (F) menambah jangkauan dengan biaya baterai lebih
cepat. Desaturasi dan bayangan biru-ungu bertambah seiring cahaya menipis.

Aturan perlindungan: **monster tidak menyerang selama lentera dibawa**, termasuk
saat charge nol. Risiko muncul setelah lentera diletakkan (G) dan pemain keluar
dari jangkauan cahayanya. Mesin tetap berbahaya kapan pun. Aturan ini membuat
lentera menjadi komitmen, bukan sekadar indikator nyawa.

## Gerak dan animasi

Enam set animasi delapan frame: `idle`, `walk`, `run`, `jump`, `glide`, `focus`.
Jalan `190 px/s`, sprint `300 px/s` dengan stamina; sprint tidak pernah
menguras charge lentera. Glide dibuka di stasiun sumbu tanpa penjaga dan dibatasi
stamina. Lompat memakai takeoff/landing yang benar-benar tersedia di dunia
kontinu.

## Monster dan mesin

Delapan bentuk monster terbuka bertahap pada 20/90/180/300/420/570/720/900 detik
atau saat charge melewati ambang masing-masing. Serangan didahului peringatan
sekitar 1,2 detik. Animasi kiri/kanan memakai pose bilateral, bukan flip
`scale.x`. Phantom dari sistem halusinasi bersifat render-only: tidak masuk
Pymunk dan tidak melukai pemain.

Dua puluh delapan mesin di rute utama bergilir lima tipe: presser (tombol →
peringatan 0,48 s → ayunan 0,14 s → tahan 0,55 s → retraksi 0,85 s → cooldown
1,5 s), duri, uap (siklus 4,8 s), balok jatuh berkawat, dan pendulum. Posisi
render dan kolisi memakai koordinat yang sama; setiap mesin punya tanda bahaya,
peringatan, dan jendela untuk menghindar.

## Puzzle dan persepsi

Puzzle memakai dua belas kategori: ColorLogic, SequenceMemory, PressurePlate,
ShadowAlignment, SoundTrigger, MirrorReflection, SymbolDecoding, TimingWindow,
SpatialReasoning, ResourceTrade, Environmental, MemoryPalace. Tombol Q
mengganti persepsi **NYATA ↔ GAUNG** secara edge-triggered dan mengubah platform
mana yang benar-benar bisa diinjak. Gerbang yang dibuka tetap terbuka saat
kembali; 144 milestone dipertahankan.

Desain ini menyampaikan gejala Alzheimer lewat mekanik, bukan dialog: jejak yang
harus diingat, objek yang hanya benar di satu persepsi, dan stasiun yang memberi
bara sekali. Tidak ada NPC, sistem hubungan, atau voice acting. Suara batin
selalu ditandai `NUR · DALAM HATI`.

## Antarmuka dan audio

HUD menampilkan charge lentera, stamina, dan akal (sanity). Jurnal/atlas (J)
membuka halaman dengan ←/→; pause dan jurnal menghentikan drain. Kontrol penuh
ada di `README.md` root.

Audio terdiri dari musik original, jump berpitch naik, landing lembut, dan tiga
lapisan stereo angin/dissonansi/napas sintetis yang berubah mengikuti cahaya.
Ekspresi audio dihasilkan dari parameter simulasi, bukan file rekaman eksternal.
