# Spesifikasi Sistem Procedural Level Generation

## Endless Survival 2D Side-Scroller menggunakan Python dan Pygame

**Jenis dokumen:** Referensi desain teknis untuk AI Agent / developer\
**Status:** Rancangan awal (belum merupakan implementasi final)\
**Target:** Sistem level tanpa akhir (*endless procedural level
generation*)\
**Teknologi:** Python, Pygame

------------------------------------------------------------------------

## 1. Tujuan Dokumen

Dokumen ini menjelaskan rancangan sistem **Procedural Level Generation**
untuk game 2D side-scroller dengan mode **Endless Survival** dan
pendekatan **Fully Procedural**.

Dokumen ini ditujukan sebagai konteks kerja bagi AI Agent yang akan
menganalisis, merancang, mengimplementasikan, menguji, atau memperbaiki
sistem tersebut.

AI Agent harus memperlakukan dokumen ini sebagai spesifikasi dasar.
Sebelum mengubah kode yang sudah ada, agent wajib memeriksa struktur
proyek, implementasi fisika pemain, sistem koordinat, collision
detection, camera, dan konvensi kode yang sudah digunakan. Jangan
mengasumsikan bahwa seluruh kode contoh atau nama modul dalam dokumen
ini sudah tersedia di proyek.

### 1.1 Tujuan utama

Sistem harus mampu:

1.  Menghasilkan platform dan geometri level secara otomatis tanpa level
    buatan tangan.
2.  Memperluas dunia ke arah kanan ketika pemain bergerak.
3.  Menjaga agar platform yang dihasilkan dapat dijangkau dengan
    kemampuan gerak pemain.
4.  Menghasilkan variasi tantangan yang meningkat secara bertahap.
5.  Menempatkan rintangan dan musuh berdasarkan aturan yang dapat
    divalidasi.
6.  Menghapus objek yang sudah jauh tertinggal agar penggunaan memori
    tetap terkendali.
7.  Menghasilkan pengalaman bermain yang bervariasi, tetapi tetap adil
    dan dapat diselesaikan.
8.  Mendukung pengujian yang dapat direproduksi menggunakan random seed.

### 1.2 Prinsip desain

-   **Fully procedural:** geometri gameplay dibuat oleh algoritma, bukan
    dengan memilih level atau chunk buatan tangan.
-   **Constraint-based:** hasil random harus tunduk pada batasan fisika,
    ruang, collision, dan keterjangkauan.
-   **Player-aware:** generator menggunakan kemampuan aktual pemain
    sebagai dasar pembuatan tantangan.
-   **Progressive difficulty:** kesulitan meningkat berdasarkan progres,
    tetapi memiliki batas dan tidak boleh membuat permainan mustahil.
-   **Streaming world:** dunia dibuat di depan pemain dan dibersihkan di
    belakang pemain.
-   **Deterministic debugging:** seed dan parameter generasi dapat
    disimpan agar masalah dapat direproduksi.
-   **Separation of concerns:** pembuatan geometri, validasi, spawning,
    rendering, dan pengelolaan kesulitan memiliki tanggung jawab
    terpisah.

------------------------------------------------------------------------

# 2. Definisi Sistem: Input, Process, dan Output

Secara konseptual, sistem memiliki tiga bagian utama:

``` text
INPUT
  |
  |-- Data fisika dan kemampuan pemain
  |-- Posisi dan progres pemain
  |-- Parameter kesulitan
  |-- Batas dunia dan konfigurasi generator
  |-- Random seed dan kondisi generasi sebelumnya
  |
  v
PROCESS
  |
  |-- Menghitung difficulty
  |-- Menentukan target geometri berikutnya
  |-- Menghasilkan kandidat platform
  |-- Memvalidasi keterjangkauan dan area landing
  |-- Menghasilkan kandidat rintangan/musuh
  |-- Memvalidasi kombinasi gameplay
  |-- Menerima atau menolak kandidat
  |-- Memasukkan objek ke world
  |-- Membersihkan objek lama
  |
  v
OUTPUT
  |
  |-- Data platform yang valid
  |-- Data rintangan dan musuh yang valid
  |-- Objek dunia yang siap di-render dan di-collision
  |-- Informasi difficulty dan progres
  |-- Data seed/log untuk debugging
```

## 2.1 Input

Input adalah seluruh data yang dibutuhkan generator sebelum membuat
bagian dunia berikutnya.

### A. Data fisika pemain

Generator harus mengetahui kemampuan gerak pemain. Nilainya harus
berasal dari konfigurasi atau implementasi Player Controller yang
benar-benar digunakan game, bukan angka perkiraan yang tidak terhubung
dengan fisika aktual.

Data minimal:

  -----------------------------------------------------------------------
  Input                   Tipe                    Keterangan
  ----------------------- ----------------------- -----------------------
  `horizontal_speed`      float                   Kecepatan gerak
                                                  horizontal pemain

  `jump_velocity`         float                   Kecepatan awal vertikal
                                                  saat melompat

  `gravity`               float                   Besar gravitasi yang
                                                  diterapkan

  `player_width`          float                   Lebar collision box
                                                  pemain

  `player_height`         float                   Tinggi collision box
                                                  pemain

  `air_control`           float/bool              Kemampuan mengendalikan
                                                  gerakan horizontal saat
                                                  di udara

  `max_fall_speed`        float                   Batas kecepatan jatuh
                                                  jika diterapkan

  `jump_mode`             enum/string             Jenis lompatan,
                                                  misalnya fixed jump
                                                  atau variable-height
                                                  jump
  -----------------------------------------------------------------------

Jika game memiliki double jump, dash, wall jump, atau kemampuan khusus
lainnya, kemampuan tersebut harus ditambahkan sebagai input eksplisit.
Jangan menganggap kemampuan tersebut tersedia jika belum
diimplementasikan.

**Catatan koordinat:** dalam Pygame, sumbu X umumnya bertambah ke kanan
dan sumbu Y bertambah ke bawah. Karena itu, kecepatan awal lompatan
biasanya bernilai negatif, sedangkan gravitasi bernilai positif.

### B. Data progres pemain

Data ini digunakan untuk menentukan bagian dunia yang perlu dibuat dan
tingkat kesulitannya.

  -----------------------------------------------------------------------
  Input                   Tipe                    Keterangan
  ----------------------- ----------------------- -----------------------
  `player_world_x`        float                   Posisi X pemain dalam
                                                  koordinat dunia

  `player_world_y`        float                   Posisi Y pemain dalam
                                                  koordinat dunia

  `distance_travelled`    float                   Jarak
                                                  horizontal/progres yang
                                                  telah ditempuh

  `survival_time`         float                   Lama pemain bertahan

  `current_score`         int/float               Skor saat ini, jika
                                                  digunakan

  `is_alive`              bool                    Status hidup pemain
  -----------------------------------------------------------------------

Posisi dunia harus dibedakan dari posisi layar. Kamera yang bergerak
tidak boleh menyebabkan generator salah menghitung jarak atau posisi
objek.

### C. Data platform sebelumnya

Platform baru dibuat dengan mengacu pada platform atau area yang sudah
ada.

Contoh struktur data:

``` python
previous_platform = {
    "x": 1200.0,
    "y": 450.0,
    "width": 240.0,
    "height": 40.0,
}
```

Data minimal platform:

-   Posisi X dan Y dunia.
-   Lebar dan tinggi.
-   Batas kiri dan kanan.
-   Permukaan atas untuk landing.
-   Status atau atribut khusus, jika ada.

Generator juga perlu mengetahui platform aktif yang relevan, bukan hanya
platform terakhir, apabila desain level memungkinkan beberapa jalur atau
platform alternatif.

### D. Parameter difficulty

Difficulty Manager menghasilkan nilai kesulitan yang kemudian
diterjemahkan menjadi parameter generator.

Contoh rentang konseptual:

``` python
difficulty = 1.0  # mudah
difficulty = 5.0  # menengah
difficulty = 10.0 # batas maksimum
```

Nilai difficulty bukan berarti semua parameter harus berubah dengan
skala yang sama. Setiap parameter harus memiliki kurva, batas minimum,
dan batas maksimum sendiri.

### E. Konfigurasi generator

Contoh konfigurasi:

``` python
GENERATOR_CONFIG = {
    "generation_distance": 1200,
    "cleanup_distance": 1000,
    "max_generation_attempts": 10,

    "platform_width_min": 130,
    "platform_width_max": 300,

    "safe_gap_ratio": 0.70,
    "max_gap_ratio": 0.80,

    "minimum_landing_width": 80,
    "minimum_safe_area": 100,
}
```

Angka di atas hanya nilai awal untuk eksperimen. Nilai final harus
ditentukan melalui pengujian dengan ukuran layar, ukuran karakter,
kecepatan, gravitasi, dan kontrol yang benar-benar dipakai game.

### F. Random seed dan state generator

Input tambahan:

-   `seed`: bilangan integer untuk menginisialisasi random number
    generator.
-   `generation_index`: urutan bagian dunia yang sedang dibuat.
-   `previous_generation_state`: data platform dan objek terakhir yang
    dibutuhkan agar generasi berkesinambungan.
-   `world_bounds`: batas vertikal atau batas ruang permainan.
-   `active_objects`: objek yang sudah berada di dunia dan dapat
    memengaruhi kandidat baru.

Gunakan instance `random.Random(seed)` atau mekanisme sejenis, bukan
random global yang sulit direproduksi.

------------------------------------------------------------------------

# 3. Process: Tahapan Pemrosesan

Bagian ini menjelaskan urutan kerja generator dari menerima input sampai
menghasilkan objek dunia yang valid.

## Tahap 1 --- Membaca state permainan

Generator menerima state terkini dari Game Manager dan World Manager.

Data yang dibaca antara lain:

1.  Posisi pemain dalam koordinat dunia.
2.  Jarak tempuh.
3.  Platform terakhir atau platform acuan.
4.  Jarak ujung dunia yang sudah dihasilkan.
5.  Daftar objek aktif.
6.  Status permainan.
7.  Seed dan indeks generasi.

Generator tidak perlu berjalan jika permainan sudah berakhir atau area
di depan pemain masih cukup jauh.

**Hasil tahap:** snapshot state yang konsisten untuk satu siklus
generasi.

## Tahap 2 --- Memeriksa kebutuhan generasi

World Manager memeriksa jarak antara pemain dan ujung dunia yang sudah
tersedia.

Contoh aturan:

``` python
if player_world_x + generation_distance > generated_until:
    request_generation()
```

`generation_distance` adalah jarak ke depan yang harus sudah tersedia.
Nilainya harus cukup untuk mencegah pemain mencapai ujung dunia yang
belum dibuat, termasuk saat pemain bergerak cepat.

Generasi dapat dilakukan beberapa platform sekaligus agar tidak
menimbulkan jeda ketika pemain mendekati batas dunia.

**Hasil tahap:** keputusan apakah generasi baru diperlukan.

## Tahap 3 --- Menghitung tingkat kesulitan

Difficulty Manager menghitung nilai difficulty dari progres pemain.

Salah satu opsi formula:

\[ D(x)=`\min`{=tex}(D\_{`\max`{=tex}},D_0+k`\ln`{=tex}(1+x/s)) \]

Keterangan:

-   (D(x)): difficulty pada jarak (x).
-   (D_0): difficulty awal.
-   (k): faktor pertumbuhan.
-   (s): faktor skala pertumbuhan.
-   (D\_{`\max`{=tex}}): batas maksimum difficulty.

Formula ini merupakan pilihan awal, bukan ketentuan mutlak. Parameter
harus diuji agar kenaikan kesulitan terasa wajar.

Contoh implementasi:

``` python
import math

class DifficultyManager:
    def __init__(self):
        self.base = 1.0
        self.growth = 1.5
        self.scale = 1000.0
        self.maximum = 10.0

    def calculate(self, distance):
        value = self.base + self.growth * math.log1p(
            max(0.0, distance) / self.scale
        )
        return min(value, self.maximum)
```

**Hasil tahap:** nilai difficulty, misalnya `3.4`, yang dipakai oleh
generator lain.

## Tahap 4 --- Mengubah difficulty menjadi parameter generasi

Generator tidak sebaiknya menggunakan nilai difficulty secara langsung
untuk semua keputusan. Nilai tersebut diterjemahkan menjadi parameter
yang jelas.

Contoh parameter:

-   Rentang lebar platform.
-   Rentang jarak antarplatform.
-   Rentang perbedaan ketinggian.
-   Probabilitas munculnya rintangan.
-   Probabilitas munculnya musuh.
-   Jumlah atau kompleksitas bahaya.
-   Ukuran area aman.

Contoh struktur:

``` python
generation_profile = {
    "platform_width_range": (150, 300),
    "gap_range": (60, 150),
    "height_delta_range": (-50, 50),
    "obstacle_probability": 0.25,
    "enemy_probability": 0.10,
}
```

Nilai ini hanya ilustrasi. Profile aktual harus dibuat melalui fungsi
atau konfigurasi yang memetakan difficulty ke rentang parameter.

**Aturan penting:** kenaikan difficulty tidak boleh melampaui batas
fisika pemain. Difficulty boleh membuat tantangan lebih ketat, tetapi
tidak boleh mengizinkan generator membuat lompatan yang mustahil.

## Tahap 5 --- Menentukan geometri platform berikutnya

Platform Generator menggunakan platform acuan untuk menentukan kandidat
platform baru.

Data yang perlu ditentukan:

1.  Posisi X platform baru.
2.  Posisi Y platform baru.
3.  Lebar platform.
4.  Tinggi/ketebalan platform.
5.  Jarak horizontal dari platform sebelumnya.
6.  Perbedaan ketinggian.
7.  Area permukaan yang dapat digunakan untuk landing.

Secara umum:

``` text
previous platform
       |
       |-- tentukan gap horizontal
       |-- tentukan perubahan ketinggian
       |-- tentukan lebar platform baru
       |-- hitung koordinat platform baru
       |
       v
candidate platform
```

Generator harus memperhatikan koordinat dunia dan batas vertikal area
permainan. Platform tidak boleh dibuat di luar area yang dapat dijangkau
atau dimainkan.

### 5.1 Perkiraan kemampuan lompatan

Untuk model fisika sederhana dengan gravitasi konstan dan tanpa batas
kecepatan jatuh:

Tinggi maksimum relatif terhadap titik lompatan:

\[ H=`\frac{v_0^2}{2g}`{=tex} \]

Waktu untuk kembali ke ketinggian awal:

\[ T=`\frac{2|v_0|}{g}`{=tex} \]

Jangkauan horizontal pada ketinggian awal yang sama, jika kecepatan
horizontal konstan:

\[ R=v_xT \]

Contoh parameter:

``` python
horizontal_speed = 250
jump_velocity = -500
gravity = 1000
```

Perkiraan ideal:

-   Tinggi maksimum: 125 piksel.
-   Waktu kembali ke ketinggian awal: 1 detik.
-   Jangkauan horizontal ideal: 250 piksel.

Angka tersebut bukan jangkauan aman. Perhitungan ideal tidak otomatis
memperhitungkan ukuran karakter, collision box, kontrol udara, waktu
reaksi, akselerasi, variable jump, atau batas kecepatan jatuh.

Generator harus memakai batas aman yang lebih kecil dan divalidasi
dengan simulasi fisika aktual.

### 5.2 Jangan hanya memeriksa jarak horizontal

Platform yang lebih tinggi memiliki waktu landing yang berbeda dari
platform dengan ketinggian sama.

Untuk model sederhana:

\[ y(t)=y_0+v_0t+`\frac{1}{2}`{=tex}gt\^2 \]

Dengan konvensi Y bertambah ke bawah, `v0` negatif saat melompat ke
atas.

Untuk mencari waktu ketika karakter mencapai ketinggian platform target,
selesaikan:

\[ y\_{`\text{target}`{=tex}}-y_0=v_0t+`\frac{1}{2}`{=tex}gt\^2 \]

Kemudian periksa apakah pada waktu tersebut posisi horizontal karakter
dapat beririsan dengan area landing platform.

Jika model Player Controller lebih kompleks, validator sebaiknya
mensimulasikan gerakan menggunakan aturan fisika yang sama dengan game,
bukan mengandalkan rumus sederhana saja.

**Hasil tahap:** kandidat platform dengan geometri lengkap.

## Tahap 6 --- Validasi platform (Reachability dan Landing)

Level Validator memeriksa kandidat platform sebelum diterima.

### A. Reachability validation

Periksa apakah pemain dapat berpindah dari platform sebelumnya ke
platform baru.

Pertimbangkan:

-   Posisi awal yang mungkin pada platform sebelumnya.
-   Ukuran collision box pemain.
-   Posisi horizontal platform target.
-   Ketinggian platform target.
-   Kecepatan horizontal dan kontrol udara.
-   Kecepatan awal lompatan dan gravitasi.
-   Batas waktu atau kecepatan jatuh jika ada.

### B. Landing validation

Pastikan platform target menyediakan ruang landing yang cukup.

Periksa:

-   Lebar efektif permukaan platform.
-   Apakah collision box pemain dapat mendarat tanpa mengenai sisi
    platform.
-   Apakah ada rintangan yang menutupi seluruh area landing.
-   Apakah platform berada di dalam batas vertikal dunia.
-   Apakah platform bertabrakan dengan geometri yang tidak semestinya.

### C. Retry dan fallback

Jika kandidat tidak valid:

1.  Tolak kandidat.
2.  Catat alasan penolakan untuk debugging.
3.  Generate kandidat baru.
4.  Validasi ulang.
5.  Ulangi sampai batas percobaan tercapai.

Contoh batas percobaan:

``` python
MAX_GENERATION_ATTEMPTS = 10
```

Jika seluruh percobaan gagal, buat platform fallback yang aman
berdasarkan parameter fisika pemain. Jangan menerima kandidat yang
diketahui tidak valid hanya untuk menjaga generasi tetap berjalan.

**Hasil tahap:** platform yang lolos validasi atau fallback aman.

## Tahap 7 --- Menghasilkan rintangan

Setelah geometri platform diterima, Obstacle Generator dapat mencoba
menempatkan rintangan.

Jenis rintangan dapat mencakup:

-   Spikes atau hazard statis.
-   Objek bergerak.
-   Rintangan gantung.
-   Lubang atau area berbahaya yang merupakan bagian geometri.
-   Objek lain yang sesuai dengan mekanik game.

Input Obstacle Generator:

-   Platform yang sudah valid.
-   Difficulty.
-   Daftar rintangan yang sudah aktif.
-   Ukuran karakter.
-   Aturan collision.
-   Probabilitas dan batas jumlah rintangan.

Proses:

1.  Tentukan apakah platform boleh memiliki rintangan.
2.  Tentukan jenis rintangan berdasarkan profile difficulty.
3.  Tentukan posisi kandidat.
4.  Pastikan kandidat berada di area platform yang sesuai.
5.  Pastikan tidak menutup seluruh area landing atau jalur wajib.
6.  Pastikan rintangan tidak bertumpuk secara tidak sengaja.
7.  Validasi apakah pemain masih memiliki jalur yang dapat dilewati.
8.  Terima atau tolak rintangan.

Probabilitas kemunculan bukan satu-satunya penentu. Generator harus
mempertimbangkan kombinasi rintangan yang sudah ada.

## Tahap 8 --- Menghasilkan musuh

Enemy Generator bekerja setelah geometri platform tersedia.

Input:

-   Platform valid.
-   Difficulty.
-   Daftar musuh aktif.
-   Batas jumlah musuh.
-   Aturan spawn dan perilaku musuh.
-   Collision box dan area gerak musuh.

Proses:

1.  Tentukan apakah musuh boleh muncul.
2.  Pilih tipe musuh yang tersedia.
3.  Tentukan posisi spawn.
4.  Periksa apakah posisi berada di platform yang valid.
5.  Periksa jarak aman dari spawn pemain dan area landing.
6.  Periksa apakah musuh dapat bergerak dalam area yang disediakan.
7.  Validasi kombinasi musuh dengan rintangan lain.
8.  Terima atau tolak kandidat.

Jenis dan perilaku musuh harus mengikuti implementasi game. Generator
tidak boleh membuat tipe musuh yang belum tersedia di proyek.

## Tahap 9 --- Validasi keseluruhan segmen

Setelah platform, rintangan, dan musuh dibuat, lakukan validasi
gabungan.

Validasi individual saja belum cukup. Platform mungkin dapat dijangkau,
tetapi rintangan dan musuh yang ditambahkan kemudian dapat membuat jalur
tersebut mustahil.

Pemeriksaan gabungan minimal:

-   Jalur dari platform sebelumnya ke platform baru tetap dapat dilalui.
-   Area landing masih cukup aman.
-   Rintangan tidak menutup seluruh jalur.
-   Musuh tidak muncul pada posisi yang tidak valid.
-   Tidak ada collision yang tidak disengaja.
-   Tidak ada objek yang keluar dari batas dunia.
-   Tidak ada kombinasi yang melanggar aturan gameplay.

Jika validasi gabungan gagal, generator dapat menghapus atau mengubah
objek tambahan terlebih dahulu. Jika masalah tetap ada, kandidat
geometri harus dibuat ulang.

**Prinsip:** validasi terakhir harus mencerminkan kondisi gameplay
setelah seluruh objek ditempatkan.

## Tahap 10 --- Memasukkan objek ke dunia

Jika semua validasi berhasil, hasil generasi diserahkan kepada World
Manager.

World Manager bertanggung jawab untuk:

-   Menyimpan objek dalam koordinat dunia.
-   Mendaftarkan platform ke sistem collision.
-   Mendaftarkan rintangan dan musuh ke sistem update.
-   Menyediakan objek untuk proses rendering.
-   Memperbarui batas dunia yang sudah dihasilkan.
-   Menyimpan informasi generasi yang diperlukan untuk debugging.

Generator sebaiknya menghasilkan data atau objek yang jelas, lalu World
Manager yang mengelola lifecycle objek tersebut.

Jangan mencampur logika menggambar layar dengan logika menentukan
geometri level.

## Tahap 11 --- Membersihkan objek lama

Ketika pemain bergerak ke kanan, objek yang sudah jauh tertinggal dapat
dihapus.

Aturan konseptual:

``` python
if object.right < player_world_x - cleanup_distance:
    remove_object(object)
```

Objek yang dihapus harus dilepaskan dari seluruh sistem yang masih
mereferensikannya, termasuk:

-   World object collection.
-   Sprite groups.
-   Collision registry.
-   Update list.
-   Object pool, jika digunakan.

Objek yang masih dibutuhkan untuk gameplay atau efek tertentu tidak
boleh dihapus terlalu cepat.

## Tahap 12 --- Mengulang siklus generasi

Setelah objek baru diterima dan objek lama dibersihkan:

1.  Perbarui `generated_until`.
2.  Simpan platform acuan terbaru.
3.  Simpan generation index.
4.  Simpan state random generator bila dibutuhkan.
5.  Tunggu sampai pemain mendekati batas generasi berikutnya.
6.  Jalankan siklus kembali.

Siklus tersebut terus berlangsung sampai pemain mati atau permainan
dihentikan.

------------------------------------------------------------------------

# 4. Output: Hasil yang Dihasilkan Sistem

Output adalah hasil akhir dari seluruh proses generasi.

## 4.1 Output utama: platform

Contoh:

``` python
platform_output = {
    "id": "platform_00042",
    "x": 2400.0,
    "y": 420.0,
    "width": 220.0,
    "height": 40.0,
    "type": "normal",
    "generation_index": 42,
}
```

Platform output harus memiliki informasi yang cukup untuk:

-   Digambar oleh renderer.
-   Digunakan collision system.
-   Menjadi acuan generasi berikutnya.
-   Dihapus oleh World Manager.
-   Dilacak ketika debugging.

## 4.2 Output rintangan

``` python
obstacle_output = {
    "id": "obstacle_00018",
    "type": "spike",
    "x": 2500.0,
    "y": 380.0,
    "width": 40.0,
    "height": 40.0,
    "generation_index": 42,
}
```

## 4.3 Output musuh

``` python
enemy_output = {
    "id": "enemy_00007",
    "type": "basic",
    "x": 2580.0,
    "y": 380.0,
    "platform_id": "platform_00042",
    "generation_index": 42,
}
```

Struktur tersebut hanya contoh. Nama field dan tipe objek harus
disesuaikan dengan desain entity yang dipakai proyek.

## 4.4 Output satu batch generasi

Lebih baik generator mengembalikan satu hasil generasi yang terstruktur
daripada mengubah banyak bagian game secara tersembunyi.

Contoh:

``` python
generation_output = {
    "generation_index": 42,
    "difficulty": 4.2,
    "seed": 123456,
    "platforms": [],
    "obstacles": [],
    "enemies": [],
    "validation": {
        "is_valid": True,
        "attempts": 2,
        "rejection_reasons": [],
    },
    "generated_until": 2840.0,
}
```

World Manager menerima hasil tersebut, kemudian memasukkan objek ke
dunia permainan.

## 4.5 Output visual dan gameplay

Ketika output diterima oleh game, hasil yang terlihat oleh pemain
adalah:

-   Platform baru muncul di depan pemain.
-   Jalur permainan terus berlanjut.
-   Jurang dan variasi ketinggian berubah.
-   Rintangan muncul sesuai tingkat kesulitan.
-   Musuh dapat muncul pada area yang valid.
-   Lingkungan visual terus berubah.
-   Bagian dunia yang sudah dilewati menghilang.

Pemain seharusnya tidak melihat batas antara satu siklus generasi dan
siklus berikutnya.

------------------------------------------------------------------------

# 5. Rancangan Modul dan Tanggung Jawab

Struktur folder yang disarankan:

``` text
game/
│
├── main.py
│
├── core/
│   ├── game_manager.py
│   ├── camera.py
│   └── settings.py
│
├── entities/
│   ├── player.py
│   ├── enemy.py
│   └── obstacle.py
│
├── procedural/
│   ├── generator.py
│   ├── generation_profile.py
│   ├── platform_generator.py
│   ├── obstacle_generator.py
│   ├── enemy_generator.py
│   ├── environment_generator.py
│   ├── difficulty_manager.py
│   └── level_validator.py
│
├── world/
│   ├── world_manager.py
│   ├── platform.py
│   └── object_pool.py
│
├── systems/
│   ├── collision.py
│   ├── physics.py
│   └── scoring.py
│
├── assets/
│   ├── images/
│   ├── sounds/
│   └── fonts/
│
└── tests/
    ├── test_generator.py
    ├── test_reachability.py
    ├── test_difficulty.py
    └── test_world_cleanup.py
```

### Tanggung jawab setiap modul

  -----------------------------------------------------------------------
  Modul                               Tanggung jawab
  ----------------------------------- -----------------------------------
  `generator.py`                      Mengorkestrasi proses generasi

  `generation_profile.py`             Mengubah difficulty menjadi
                                      parameter

  `platform_generator.py`             Membuat kandidat geometri platform

  `obstacle_generator.py`             Membuat kandidat rintangan

  `enemy_generator.py`                Membuat kandidat musuh

  `environment_generator.py`          Membuat dekorasi dan variasi visual

  `difficulty_manager.py`             Menghitung tingkat kesulitan

  `level_validator.py`                Memvalidasi geometri dan kombinasi
                                      gameplay

  `world_manager.py`                  Menambah, menyimpan, memperbarui,
                                      dan menghapus objek

  `platform.py`                       Representasi platform di dunia

  `object_pool.py`                    Opsional: menggunakan ulang objek
                                      untuk mengurangi alokasi berulang

  `physics.py`                        Aturan fisika yang dipakai pemain
                                      dan validator

  `collision.py`                      Pemeriksaan tabrakan aktual
  -----------------------------------------------------------------------

Nama modul di atas adalah rancangan. Agent boleh menyesuaikan dengan
arsitektur proyek yang sudah ada, tetapi tanggung jawabnya harus tetap
terpisah.

------------------------------------------------------------------------

# 6. Alur Integrasi Antar-Modul

Alur pemanggilan yang disarankan:

``` text
Game Loop
   |
   v
Game Manager
   |
   |-- membaca player state
   |-- membaca world state
   |
   v
World Manager
   |
   |-- apakah perlu generate?
   |
   v
Procedural Generator
   |
   |-- Difficulty Manager
   |       |
   |       v
   |   Generation Profile
   |
   |-- Platform Generator
   |       |
   |       v
   |   Level Validator
   |
   |-- Obstacle Generator
   |       |
   |       v
   |   Level Validator
   |
   |-- Enemy Generator
   |       |
   |       v
   |   Level Validator
   |
   |-- Final Segment Validation
   |
   v
Generation Output
   |
   v
World Manager
   |
   |-- register objects
   |-- update generated boundary
   |-- cleanup old objects
   |
   v
Collision System + Renderer
```

Generator tidak perlu dipanggil pada setiap frame. Pemanggilan dilakukan
ketika dunia membutuhkan tambahan area. Update fisika, collision, dan
rendering tetap berjalan sesuai game loop.

------------------------------------------------------------------------

# 7. Pseudocode Siklus Generasi

Pseudocode berikut menggambarkan alur utama. Ini bukan implementasi
final dan tidak mengasumsikan API tertentu dari proyek.

``` python
def generate_next_segment(world, player, config):
    # 1. Ambil state dunia
    state = world.get_generation_state()

    # 2. Hitung difficulty
    difficulty = difficulty_manager.calculate(
        player.distance_travelled
    )

    # 3. Ubah difficulty menjadi parameter
    profile = generation_profile.create(difficulty)

    # 4. Siapkan generator acak
    rng = state.random_generator

    # 5. Generate dan validasi platform
    platform = platform_generator.generate_valid(
        previous_platform=state.last_platform,
        profile=profile,
        player_physics=player.physics,
        validator=level_validator,
        rng=rng,
    )

    if platform is None:
        platform = platform_generator.create_safe_fallback(
            state.last_platform,
            player.physics,
        )

    # 6. Generate rintangan
    obstacles = obstacle_generator.generate(
        platform=platform,
        profile=profile,
        rng=rng,
    )

    # 7. Generate musuh
    enemies = enemy_generator.generate(
        platform=platform,
        profile=profile,
        rng=rng,
    )

    # 8. Validasi keseluruhan segmen
    segment = {
        "platforms": [platform],
        "obstacles": obstacles,
        "enemies": enemies,
    }

    if not level_validator.validate_segment(
        segment,
        state,
        player.physics,
    ):
        segment = level_validator.repair_or_fallback(
            segment,
            state,
            player.physics,
        )

    # 9. Kirim hasil ke World Manager
    world.add_segment(segment)

    # 10. Simpan state generasi
    world.update_generation_state(segment)

    return segment
```

------------------------------------------------------------------------

# 8. Kesulitan Adaptif dan Fairness

Difficulty yang meningkat tidak boleh hanya berarti jumlah objek
berbahaya semakin banyak.

Generator harus mengatur beberapa dimensi kesulitan secara terpisah:

  Dimensi    Contoh perubahan
  ---------- ------------------------------------
  Geometri   Lebar platform dan jarak jurang
  Vertikal   Perbedaan ketinggian platform
  Timing     Kecepatan atau pola objek bergerak
  Hazard     Jumlah dan kombinasi rintangan
  Enemy      Frekuensi dan variasi musuh
  Recovery   Ketersediaan platform aman

### 8.1 Batas fairness

Tetapkan aturan yang tidak boleh dilanggar:

1.  Semua lompatan wajib memiliki solusi yang dapat dijalankan.
2.  Ukuran landing harus memperhitungkan collision box pemain.
3.  Jangan menempatkan bahaya yang menutup semua area landing.
4.  Jangan menempatkan musuh pada posisi spawn yang tidak dapat
    dihindari.
5.  Difficulty tidak boleh melewati batas fisika pemain.
6.  Berikan variasi ruang aman atau jeda agar tantangan tidak selalu
    meningkat tanpa kesempatan recovery.
7.  Jika pemain memiliki kemampuan khusus, validator harus menghitung
    kemampuan tersebut secara konsisten.

### 8.2 Dynamic Difficulty Adjustment (opsional)

Pada tahap awal, difficulty cukup dihitung dari jarak tempuh.

Setelah sistem dasar stabil, performa pemain dapat dipakai sebagai
sinyal tambahan, misalnya:

-   Frekuensi gagal melompat.
-   Jumlah tabrakan.
-   Lama bertahan.
-   Keberhasilan melewati rintangan.

Sistem dapat mengurangi atau menahan kenaikan kesulitan ketika pemain
mengalami banyak kegagalan.

Fitur ini bersifat opsional dan tidak perlu dibuat sebelum generator
dasar berfungsi.

------------------------------------------------------------------------

# 9. Random Seed dan Reproducibility

Setiap sesi permainan sebaiknya memiliki seed.

Contoh:

``` python
import random

seed = 123456
rng = random.Random(seed)
```

Semua keputusan random dalam satu generator harus menggunakan instance
RNG yang sama atau stream RNG yang dikelola dengan jelas.

Manfaat seed:

-   Mengulang susunan dunia yang sama.
-   Mereproduksi bug generasi.
-   Membandingkan perubahan algoritma.
-   Menguji apakah perubahan validator memperbaiki hasil.
-   Membuat pengujian otomatis yang konsisten.

Log debugging sebaiknya mencatat:

``` python
debug_info = {
    "seed": seed,
    "generation_index": generation_index,
    "difficulty": difficulty,
    "attempts": attempts,
    "rejection_reasons": rejection_reasons,
}
```

Catatan: seed yang sama hanya menjamin hasil yang sama jika urutan
pemanggilan random, versi algoritma, dan parameter generasi juga sama.

------------------------------------------------------------------------

# 10. Pengujian dan Kriteria Penerimaan

Sistem belum dapat dianggap selesai hanya karena platform berhasil
muncul.

## 10.1 Unit test

Uji masing-masing komponen:

-   Difficulty Manager menghasilkan nilai dalam batas yang ditentukan.
-   Platform Generator menghasilkan koordinat dan ukuran yang valid.
-   Level Validator menolak platform yang tidak dapat dijangkau.
-   Obstacle Generator tidak menempatkan rintangan di luar platform.
-   Enemy Generator tidak menempatkan musuh pada posisi spawn yang tidak
    valid.
-   World Manager menghapus objek yang sudah melewati batas cleanup.

## 10.2 Simulation test

Jalankan generator tanpa rendering untuk menghasilkan banyak segmen.

Pengujian yang disarankan:

-   1.000 generasi untuk pemeriksaan awal.
-   10.000 generasi dengan beberapa seed untuk pengujian lanjutan.
-   Uji pada difficulty rendah, menengah, dan maksimum.
-   Catat jumlah percobaan ulang.
-   Catat frekuensi fallback.
-   Catat alasan kandidat ditolak.
-   Periksa apakah ada segmen yang tidak dapat diselesaikan.

Angka tersebut merupakan target pengujian awal, bukan jaminan bahwa
sistem bebas bug.

## 10.3 Integration test

Uji di dalam Pygame:

-   Pemain dapat bergerak tanpa mencapai ujung dunia yang belum dibuat.
-   Platform baru tersambung dengan jalur sebelumnya.
-   Collision sesuai dengan geometri yang dihasilkan.
-   Kamera tidak mengganggu koordinat dunia.
-   Objek lama benar-benar dibersihkan.
-   Jumlah objek aktif tetap terkendali.
-   Tidak ada jeda besar saat generasi berlangsung.

## 10.4 Acceptance criteria

Sistem dapat dianggap mencapai versi awal yang layak apabila:

1.  Dunia terus dihasilkan selama pemain masih hidup.
2.  Generator tidak bergantung pada level atau chunk buatan tangan.
3.  Platform yang diterima lolos validasi keterjangkauan.
4.  Rintangan dan musuh lolos validasi penempatan.
5.  Ada fallback aman ketika generasi gagal.
6.  Kesulitan meningkat sesuai progres dan memiliki batas maksimum.
7.  Objek lama dibersihkan.
8.  Seed dapat digunakan untuk mereproduksi masalah.
9.  Generator dapat diuji tanpa harus menjalankan seluruh game.
10. Tidak ada pertumbuhan objek aktif tanpa batas selama sesi panjang.

------------------------------------------------------------------------

# 11. Optimasi Performa

Beberapa prinsip optimasi:

### A. Generate di depan pemain

Siapkan area sebelum pemain mencapainya. Jangan menunggu sampai pemain
benar-benar berada di ujung dunia.

### B. Jangan generate setiap frame

Gunakan trigger berbasis jarak atau kebutuhan world manager.

### C. Batasi jumlah percobaan

Gunakan `max_generation_attempts` agar kandidat buruk tidak membuat loop
generasi berlangsung tanpa batas.

### D. Gunakan object pooling jika diperlukan

Object pooling berguna untuk objek yang sering dibuat dan dihancurkan,
tetapi tidak wajib untuk semua objek. Ukur performa terlebih dahulu.

### E. Pisahkan update dan render

Generator bertugas menghasilkan data dunia. Renderer bertugas menggambar
objek yang terlihat kamera.

### F. Batasi objek aktif

Objek yang terlalu jauh di belakang pemain harus dibersihkan. Dekorasi
yang tidak terlihat dapat dikelola terpisah dari objek gameplay.

### G. Hindari validasi berulang yang tidak perlu

Simpan hasil validasi atau data geometri yang sudah dihitung jika masih
relevan dan tidak berubah.

------------------------------------------------------------------------

# 12. Hal yang Belum Ditentukan

Dokumen ini menetapkan arsitektur dasar, tetapi beberapa detail perlu
dipastikan dari proyek dan desain game sebelum implementasi final.

  -----------------------------------------------------------------------
  Hal                                 Status
  ----------------------------------- -----------------------------------
  Ukuran resolusi game                Belum ditentukan

  Ukuran karakter dan collision box   Harus dibaca dari implementasi

  Kecepatan horizontal pemain         Harus dibaca dari implementasi

  Nilai gravitasi dan jump velocity   Harus dibaca dari implementasi

  Apakah pemain memiliki double       Belum ditentukan
  jump/dash                           

  Batas vertikal dunia                Perlu ditentukan

  Jenis musuh                         Mengikuti desain game

  Jenis rintangan                     Mengikuti desain game

  Sistem skor                         Perlu disesuaikan

  Apakah difficulty memakai jarak     Rekomendasi awal: jarak
  atau waktu                          

  Apakah ada dynamic difficulty       Opsional, bukan prioritas awal

  Apakah platform bergerak            Belum ditentukan; jangan
                                      diasumsikan tersedia
  -----------------------------------------------------------------------

AI Agent tidak boleh mengarang keputusan untuk hal-hal tersebut. Periksa
kode dan dokumentasi proyek, lalu ajukan pertanyaan hanya jika informasi
yang hilang benar-benar menghambat implementasi.

------------------------------------------------------------------------

# 13. Urutan Implementasi yang Direkomendasikan

Implementasi sebaiknya dilakukan bertahap agar kesalahan mudah
ditemukan.

## Phase 1 --- Memahami fondasi game

1.  Periksa struktur proyek.
2.  Identifikasi Player Controller.
3.  Identifikasi sistem fisika dan collision.
4.  Identifikasi sistem koordinat dunia dan kamera.
5.  Catat parameter fisika aktual.
6.  Buat ringkasan asumsi dan risiko integrasi.

**Output:** laporan kondisi proyek dan spesifikasi parameter pemain.

## Phase 2 --- Platform generation dasar

1.  Buat Platform Generator.
2.  Generate platform awal.
3.  Generate platform berikutnya berdasarkan platform sebelumnya.
4.  Terapkan batas lebar, gap, dan ketinggian.
5.  Visualisasikan hasil generasi.
6.  Pastikan collision bekerja.

**Output:** platform dapat dibuat secara otomatis dan tersambung secara
geometris.

## Phase 3 --- Reachability validation

1.  Hitung estimasi lintasan lompatan.
2.  Perhitungkan ukuran karakter.
3.  Validasi area landing.
4.  Tambahkan retry.
5.  Tambahkan fallback aman.
6.  Uji dengan banyak seed.

**Output:** platform yang diterima dapat dijangkau berdasarkan model
gerak pemain.

## Phase 4 --- Infinite world

1.  Buat World Manager.
2.  Tambahkan generation trigger.
3.  Spawn area baru di depan pemain.
4.  Hapus objek di belakang pemain.
5.  Pastikan koordinat kamera dan dunia konsisten.

**Output:** dunia terus berlanjut tanpa harus memuat seluruh level
sekaligus.

## Phase 5 --- Difficulty scaling

1.  Buat Difficulty Manager.
2.  Hubungkan progres pemain dengan difficulty.
3.  Buat Generation Profile.
4.  Hubungkan profile dengan parameter platform.
5.  Uji kurva kesulitan.

**Output:** geometri level berkembang secara bertahap.

## Phase 6 --- Gameplay generation

1.  Tambahkan Obstacle Generator.
2.  Tambahkan validasi rintangan.
3.  Tambahkan Enemy Generator.
4.  Validasi kombinasi seluruh objek.
5.  Tambahkan variasi pola dan ruang aman.

**Output:** dunia memiliki tantangan yang lebih beragam.

## Phase 7 --- Environment dan optimasi

1.  Tambahkan Environment Generator.
2.  Pisahkan dekorasi dari collision gameplay.
3.  Tambahkan parallax dan variasi visual.
4.  Ukur performa.
5.  Terapkan object pooling jika diperlukan.
6.  Jalankan stress test.

**Output:** endless world yang lebih menarik dan stabil.

------------------------------------------------------------------------

# 14. Instruksi Kerja untuk AI Agent

Gunakan bagian ini sebagai pedoman ketika mengerjakan proyek.

## 14.1 Sebelum menulis kode

AI Agent wajib:

1.  Membaca struktur proyek yang sudah ada.
2.  Membaca kode Player Controller dan sistem fisika.
3.  Membaca implementasi collision dan camera.
4.  Mengidentifikasi pola arsitektur dan penamaan yang digunakan.
5.  Menentukan file mana yang perlu dibuat atau diubah.
6.  Menyampaikan rencana implementasi sebelum melakukan perubahan besar.

Jangan langsung membuat ulang sistem game jika sebagian komponennya
sudah tersedia.

## 14.2 Saat implementasi

AI Agent harus:

-   Mengikuti tanggung jawab modul pada dokumen ini.
-   Menggunakan parameter fisika aktual.
-   Memisahkan generasi kandidat dan validasi.
-   Memastikan semua loop retry memiliki batas.
-   Menyediakan fallback yang aman.
-   Menggunakan random seed yang dapat direproduksi.
-   Menjaga generator tidak bergantung pada rendering.
-   Tidak menambahkan mekanik pemain yang belum disetujui.
-   Tidak mengubah gameplay inti tanpa alasan dan penjelasan.

## 14.3 Saat pengujian

AI Agent harus:

-   Menjalankan unit test yang relevan.
-   Menguji banyak seed.
-   Menguji beberapa tingkat difficulty.
-   Mencatat kegagalan validasi.
-   Memeriksa kemungkinan infinite loop.
-   Memeriksa penggunaan memori selama sesi panjang.
-   Menjelaskan keterbatasan validator.

Jangan mengklaim generator bebas level mustahil hanya karena beberapa
percobaan manual berhasil.

## 14.4 Saat melaporkan hasil

Setiap tahap implementasi harus dilaporkan dengan format:

1.  **Tujuan:** apa yang dikerjakan.
2.  **File berubah:** file yang dibuat atau dimodifikasi.
3.  **Implementasi:** bagaimana sistem bekerja.
4.  **Input:** data yang digunakan.
5.  **Process:** proses yang dijalankan.
6.  **Output:** hasil yang dihasilkan.
7.  **Pengujian:** test yang dijalankan dan hasilnya.
8.  **Keterbatasan:** hal yang belum diselesaikan.
9.  **Langkah berikutnya:** pekerjaan yang direkomendasikan.

------------------------------------------------------------------------

# 15. Ringkasan Spesifikasi

  -----------------------------------------------------------------------
  Bagian                              Spesifikasi
  ----------------------------------- -----------------------------------
  Genre/format                        2D side-scroller

  Mode                                Endless Survival

  Generasi level                      Fully Procedural

  Pendekatan                          Constraint-Based Generation

  Bahasa                              Python

  Framework                           Pygame

  Arah dunia                          Horizontal ke kanan

  Input utama                         Fisika pemain, posisi dunia,
                                      progres, difficulty, seed,
                                      konfigurasi

  Proses utama                        Generate geometri, validasi,
                                      generate objek, final validation,
                                      spawn, cleanup

  Output utama                        Platform, rintangan, musuh,
                                      dekorasi, dan state dunia

  Kesulitan                           Meningkat berdasarkan jarak tempuh,
                                      dengan batas maksimum

  Validasi                            Reachability, landing, obstacle,
                                      enemy, dan segment validation

  Pengelolaan dunia                   Streaming generation dan cleanup

  Pengujian                           Unit test, simulation test,
                                      integration test, stress test

  Reproducibility                     Random seed dan generation log
  -----------------------------------------------------------------------

## Prinsip paling penting

**Generator tidak boleh sekadar menghasilkan level yang terlihat acak.
Generator harus menghasilkan level yang valid, dapat dijangkau, adil,
dan sesuai dengan kemampuan aktual pemain.**

Prioritas implementasi adalah:

1.  Platform generation.
2.  Reachability validation.
3.  Infinite world.
4.  Difficulty scaling.
5.  Obstacle dan enemy generation.
6.  Environment generation.
7.  Optimasi dan stress testing.

Sistem dasar dianggap berhasil ketika pemain dapat terus bergerak
melalui dunia yang dihasilkan algoritma, tanpa level buatan tangan,
tanpa mencapai ujung dunia yang belum dibuat, dan tanpa dipaksa
menghadapi geometri yang mustahil diselesaikan.
