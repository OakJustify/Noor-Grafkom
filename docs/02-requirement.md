# 02 — Requirements

Dokumen ini mendefinisikan kebutuhan konkret yang harus dipenuhi proyek **Noor** agar tujuan pada `01-overview.md` tercapai. Dokumen ini **tidak** menjelaskan cara implementasi (lihat `03-architecture.md`), rancangan visual (lihat `04-design.md`), spesifikasi fitur terperinci (lihat `05-specifications.md`), jadwal (lihat `06-planning.md`), atau strategi pengujian (lihat `07-testing.md`).

Setiap kebutuhan diberi ID agar dapat dilacak ke acceptance criteria dan ke pengujian.

---

## 1. Functional Requirements

Menjelaskan fungsi dan kemampuan yang harus dimiliki proyek.

### 1.1 Startup & Menu

- **FR-01 — Game dapat dijalankan.**
  Game harus dapat dimulai dari entry point `src/play_nur.py` tanpa error pada environment pengembangan yang telah ditentukan.

- **FR-02 — Menu utama tersedia.**
  Game harus menampilkan menu utama yang memungkinkan pemain memulai permainan, melihat informasi singkat, dan keluar dari game.

- **FR-03 — Kontrol keluar dan pause.**
  Pemain harus dapat menjeda permainan dan keluar dari game kapan saja melalui kontrol yang jelas.

### 1.2 Gameplay & Interaksi

- **FR-04 — Pemain dapat mengendalikan karakter.**
  Pemain harus dapat menggerakkan karakter utama dan berinteraksi dengan objek atau elemen dalam scene menggunakan input keyboard (dan/atau mouse) yang telah ditentukan.

- **FR-05 — Progresi naratif berjalan.**
  Game harus menyampaikan cerita secara bertahap melalui scene atau urutan kejadian, sehingga pemain mengalami perjalanan karakter dari awal hingga akhir.

- **FR-06 — Transisi antar scene.**
  Game harus dapat berpindah antar scene (misalnya dari ruang awal ke ruang berikutnya) sesuai alur cerita.

- **FR-07 — Interaksi dengan objek atau kejadian dalam scene.**
  Pemain harus dapat memicu kejadian tertentu (misalnya dialog, petunjuk, atau perubahan scene) melalui interaksi yang telah dirancang.

### 1.3 Rendering & Audio

- **FR-08 — Aset game dirender dengan pycairo.**
  Aset visual utama game (setidaknya elemen yang telah ditetapkan dalam spesifikasi) harus digambar menggunakan pycairo, sesuai ketentuan mata kuliah Grafika Komputer.

- **FR-09 — Game loop dan window menggunakan pygame.**
  pygame harus digunakan untuk mengelola game loop, jendela, input, dan sinkronisasi frame.

- **FR-10 — Audio diputar melalui pygame.**
  Efek suara dan/atau musik latar harus dapat diputar dan dihentikan sesuai kebutuhan scene.

### 1.4 Penyampaian Pesan Edukatif

- **FR-11 — Pesan edukasi tentang Alzheimer tersampaikan.**
  Game harus menyampaikan informasi tentang Alzheimer melalui narasi, dialog, atau elemen gameplay, tanpa menyebutkan diagnosis secara langsung di awal permainan.

- **FR-12 — Gejala dan kesulitan penderita Alzheimer direpresentasikan.**
  Gameplay harus merepresentasikan setidaknya beberapa gejala atau kesulitan yang dialami penderita Alzheimer (misalnya kebingungan, lupa, disorientasi) sesuai rancangan pada `04-design.md` dan `05-specifications.md`.

- **FR-13 — Penutup atau ending tersedia.**
  Game harus memiliki akhir yang jelas, yang mengungkapkan konteks Alzheimer kepada pemain dan menyampaikan pesan edukatif.

### 1.5 Build & Dokumentasi

- **FR-14 — Build dapat dijalankan secara lokal.**
  Proyek harus menghasilkan build atau cara menjalankan game secara lokal yang dapat didemokan kepada dosen dan penguji.

- **FR-15 — Dokumentasi proyek tersedia.**
  Proyek harus menyertakan dokumentasi minimum: `01-overview.md`, `02-requirement.md`, `03-architecture.md`, `04-design.md`, `05-specifications.md`, `06-planning.md`, `07-testing.md`, `08-ai-guidelines.md`, `09-decisions.md`, `CHANGELOG.md`, `PROJECT-STATUS.md`, dan `README.md` sesuai struktur folder `docs/`.

---

## 2. Non-Functional Requirements

Menjelaskan kualitas atau karakteristik yang diharapkan dari proyek.

- **NFR-01 — Performa.**
  Game harus berjalan pada frame rate yang stabil di lingkungan pengembangan target (target minimum ditetapkan di `05-specifications.md`), tanpa penurunan performa yang mengganggu gameplay.

- **NFR-02 — Kompatibilitas.**
  Game harus dapat dijalankan pada setidaknya satu sistem operasi desktop target (Windows, Linux, atau macOS) yang ditetapkan tim, dengan Python, pygame, dan pycairo yang terpasang.

- **NFR-03 — Usability.**
  Kontrol dan antarmuka harus dapat dipahami oleh pengguna baru tanpa pelatihan khusus, dengan petunjuk kontrol yang ditampilkan di dalam game.

- **NFR-04 — Accessibility.**
  Game harus memperhatikan keterbacaan teks (ukuran font, kontras warna) dan tidak mengandalkan warna semata untuk menyampaikan informasi penting.

- **NFR-05 — Reliability.**
  Game tidak boleh crash pada alur utama permainan. Kesalahan yang tidak terduga harus ditangani agar tidak menghentikan game secara paksa.

- **NFR-06 — Offline.**
  Game harus dapat dimainkan sepenuhnya tanpa koneksi internet.

- **NFR-07 — Maintainability.**
  Kode harus terstruktur dalam modul yang jelas (misalnya `src/`) dan dapat dipahami oleh anggota tim lain, dengan penamaan yang konsisten dan pemisahan tanggung jawab yang wajar.

- **NFR-08 — Representasi yang hormat.**
  Penggambaran karakter dengan Alzheimer harus dilakukan secara hormat, tidak merendahkan, dan tidak memperkuat stigma.

---

## 3. User & Stakeholder Requirements

Menjelaskan kebutuhan pihak-pihak yang berkepentingan terhadap proyek.

### 3.1 Pemain (anak-anak hingga dewasa, mahasiswa, masyarakat umum)

- **USR-01 — Pengalaman bermain yang engaging.**
  Pemain membutuhkan alur cerita dan interaksi yang cukup menarik agar mau memainkan game hingga akhir.

- **USR-02 — Kontrol yang jelas.**
  Pemain membutuhkan penjelasan kontrol yang mudah dipahami, terutama bagi yang belum terbiasa bermain game.

- **USR-03 — Pesan yang mudah dipahami.**
  Pemain membutuhkan penyampaian pesan tentang Alzheimer yang tidak rumit dan tidak menakutkan.

- **USR-04 — Durasi yang wajar.**
  Pemain membutuhkan pengalaman bermain yang tidak terlalu panjang, mengingat tujuan utamanya adalah edukasi singkat.

### 3.2 Dosen Grafika Komputer

- **USR-05 — Penerapan pycairo terlihat jelas.**
  Dosen membutuhkan bukti bahwa pycairo digunakan untuk penggambaran aset game, sesuai ketentuan mata kuliah.

- **USR-06 — Penerapan pygame terlihat jelas.**
  Dosen membutuhkan bukti bahwa pygame digunakan untuk game loop, input, window, dan audio.

- **USR-07 — Kualitas kode dan dokumentasi.**
  Dosen membutuhkan kode yang dapat dibaca dan dokumentasi yang lengkap untuk menilai proyek.

### 3.3 Tim Pengembang

- **USR-08 — Scope yang manageable.**
  Tim membutuhkan ruang lingkup yang dapat diselesaikan dalam batas waktu mata kuliah.

- **USR-09 — Pembagian peran yang jelas.**
  Tim membutuhkan pembagian tanggung jawab yang jelas antar anggota (project manager, illustrator, coder, audio & music artist).

### 3.4 Penderita Alzheimer dan Keluarga/Pengasuh

- **USR-10 — Representasi yang tidak merendahkan.**
  Penderita Alzheimer dan keluarganya membutuhkan penggambaran yang hormat dan tidak memperkuat stigma.

- **USR-11 — Pesan empati yang akurat.**
  Keluarga dan pengasuh membutuhkan penyampaian kesulitan nyata penderita Alzheimer agar masyarakat lebih memahami mereka.

### 3.5 Potensi Konflik Antarkebutuhan

- **USR-12 — Keseimbangan antara edukasi dan hiburan.**
  Terdapat potensi ketegangan antara kebutuhan menyampaikan pesan edukatif yang akurat (USR-11) dan kebutuhan membuat game yang engaging (USR-01). Prioritas diberikan pada akurasi pesan, dengan gameplay sebagai sarana, bukan tujuan.

- **USR-13 — Keseimbangan antara scope dan kualitas.**
  Terdapat potensi ketegangan antara keinginan menambah fitur (USR-08) dan batas waktu mata kuliah (lihat bagian 5). Prioritas diberikan pada penyelesaian alur utama yang berfungsi.

---

## 4. Data & Resource Requirements

Menjelaskan data dan sumber daya yang dibutuhkan proyek.

### 4.1 Aset

- **DR-01 — Aset visual.**
  Proyek membutuhkan aset visual (karakter, background, elemen UI, dan sebagainya) yang disimpan di `assets/`. Sebagian aset digambar secara programatik dengan pycairo.

- **DR-02 — Aset audio.**
  Proyek membutuhkan efek suara dan/atau musik latar yang disimpan di `assets/` dan diputar melalui pygame.

- **DR-03 — Font.**
  Proyek membutuhkan font yang mendukung keterbacaan teks (lihat NFR-04) dan disimpan di `assets/`.

### 4.2 Kode dan Dokumentasi

- **DR-04 — Kode sumber.**
  Proyek membutuhkan kode sumber Python yang terstruktur di `src/`, dengan entry point `src/play_nur.py`.

- **DR-05 — Pengujian.**
  Proyek membutuhkan kode atau skenario pengujian di `tests/` sesuai `07-testing.md`.

- **DR-06 — Dokumentasi.**
  Proyek membutuhkan dokumentasi di `docs/` sesuai struktur yang telah ditetapkan.

### 4.3 Perangkat Lunak dan Lingkungan

- **DR-07 — Python.**
  Proyek membutuhkan Python versi yang ditetapkan tim (lihat `05-specifications.md`).

- **DR-08 — Library wajib.**
  Proyek membutuhkan `pygame` dan `pycairo`. Library tambahan (jika ada, misalnya `numpy`) harus didokumentasikan di `05-specifications.md` dan referensinya ditambahkan ke OVR-009.

- **DR-09 — Virtual environment.**
  Proyek membutuhkan virtual environment (`.venv-nur`) untuk menjalankan game secara konsisten.

- **DR-10 — Lingkungan pengembangan.**
  Proyek membutuhkan perangkat desktop dengan display dan audio untuk pengembangan dan pengujian.

### 4.4 Data

- **DR-11 — Tidak ada data eksternal.**
  Proyek tidak membutuhkan database, API, atau layanan online. Seluruh konten bersifat lokal dan statis.

- **DR-12 — Tidak ada data pengguna.**
  Proyek tidak mengumpulkan data pribadi pengguna (sesuai OVR-030: tanpa analitik pengguna, tanpa cloud save).

---

## 5. Constraints & Limitations

Menjelaskan batasan yang harus diperhatikan.

- **CON-01 — Batas waktu akademik.**
  Proyek harus selesai sesuai deadline mata kuliah Grafika Komputer.

- **CON-02 — Tim kecil.**
  Proyek dikerjakan oleh 4 orang dengan peran ganda (lihat OVR-006 dan bagian 14 `01-overview.md`).

- **CON-03 — Tanpa anggaran khusus.**
  Proyek tidak memiliki anggaran; aset harus dibuat sendiri, menggunakan sumber gratis, atau digambar secara programatik.

- **CON-04 — Platform desktop saja.**
  Proyek hanya menargetkan desktop; versi mobile tidak termasuk (lihat OVR-030, OVR-033).

- **CON-05 — Offline dan single-player.**
  Proyek tidak mendukung multiplayer, backend online, cloud save, atau analitik (lihat OVR-030, OVR-044).

- **CON-06 — Teknologi terbatas.**
  Proyek menggunakan Python dengan pygame dan pycairo; teknologi lain hanya jika benar-benar diperlukan dan didokumentasikan.

- **CON-07 — Bukan alat medis.**
  Proyek tidak boleh digunakan untuk diagnosis, pengobatan, atau klaim klinis (lihat OVR-045).

- **CON-08 — Konten terbatas.**
  Kedalaman konten edukasi terbatas pada apa yang dapat disampaikan dalam satu sesi permainan singkat.

- **CON-09 — Belum divalidasi secara klinis.**
  Konten edukasi belum divalidasi oleh ahli medis; ini harus dinyatakan secara eksplisit di dalam game atau dokumentasi.

- **CON-10 — Tidak ada lokalisasi multi-bahasa.**
  Versi saat ini hanya dalam satu bahasa (lihat OVR-033).

---

## 6. Acceptance Criteria

Menjelaskan kondisi yang harus terpenuhi agar kebutuhan atau proyek dianggap berhasil.

### 6.1 Kriteria Fungsional

- **AC-01 — Game dapat dijalankan.**
  `src/play_nur.py` berhasil dijalankan di environment target tanpa error, dan jendela game muncul.

- **AC-02 — Alur utama dapat diselesaikan.**
  Pemain dapat menyelesaikan permainan dari menu utama hingga ending tanpa hambatan yang menghentikan permainan.

- **AC-03 — Kontrol berfungsi.**
  Seluruh kontrol yang didokumentasikan merespons input dengan benar.

- **AC-04 — Transisi scene berjalan.**
  Perpindahan antar scene terjadi sesuai alur dan tidak menyebabkan crash.

- **AC-05 — Audio berfungsi.**
  Audio yang dirancang untuk diputar pada scene tertentu benar-benar terdengar dan dapat dihentikan.

- **AC-06 — pycairo digunakan untuk aset.**
  Aset yang ditetapkan dalam spesifikasi terbukti digambar menggunakan pycairo (dapat diverifikasi dari kode).

- **AC-07 — pygame digunakan untuk game loop.**
  Game loop, window, input, dan audio dikelola melalui pygame (dapat diverifikasi dari kode).

- **AC-08 — Pesan edukasi tersampaikan.**
  Setidaknya satu elemen narasi atau gameplay menyampaikan informasi tentang Alzheimer, dan ending mengungkapkan konteks penyakit secara jelas.

### 6.2 Kriteria Non-Fungsional

- **AC-09 — Performa stabil.**
  Game berjalan pada frame rate target di environment pengembangan tanpa lag yang mengganggu.

- **AC-10 — Berjalan offline.**
  Game dapat dimainkan tanpa koneksi internet.

- **AC-11 — Tidak crash pada alur utama.**
  Pengujian alur utama (lihat `07-testing.md`) tidak menemukan crash.

- **AC-12 — Teks terbaca.**
  Teks pada resolusi target dapat dibaca tanpa kesulitan.

### 6.3 Kriteria Akademik

- **AC-13 — Dokumentasi lengkap.**
  Seluruh file di `docs/` tersedia dan terisi sesuai strukturnya.

- **AC-14 — Memenuhi ketentuan mata kuliah.**
  Proyek memenuhi kriteria penilaian Grafika Komputer, termasuk penerapan pycairo dan pygame yang dapat diverifikasi.

- **AC-15 — Dapat didemokan.**
  Proyek dapat didemokan kepada dosen dan penguji dalam bentuk build yang dapat dijalankan.

### 6.4 Kriteria Etis

- **AC-16 — Representasi yang hormat.**
  Tidak ada elemen dalam game yang merendahkan penderita Alzheimer atau memperkuat stigma.

- **AC-17 — Disclaimer tersedia.**
  Game atau dokumentasi menyatakan secara eksplisit bahwa Noor bukan alat medis dan belum divalidasi secara klinis.

---

## 7. Hal yang Tidak Termasuk dalam Dokumen Ini

Agar tidak tumpang tindih dengan dokumen lain:

- **Cara implementasi fitur** → `03-architecture.md`, `05-specifications.md`
- **Rancangan visual dan pengalaman pengguna** → `04-design.md`
- **Detail teknis setiap fitur (parameter, state, format data)** → `05-specifications.md`
- **Jadwal dan pembagian kerja** → `06-planning.md`
- **Skenario dan metode pengujian** → `07-testing.md`
- **Keputusan desain dan alasannya** → `09-decisions.md`

---

## 8. Catatan Terbuka

Beberapa hal masih perlu dikonfirmasi oleh tim dan dapat memengaruhi isi dokumen ini:

- Target frame rate minimum (NFR-01) dan resolusi target (NFR-04).
- Sistem operasi target utama (NFR-02).
- Versi Python dan library tambahan yang digunakan (DR-07, DR-08).
- Daftar scene dan mekanik gameplay yang pasti, yang akan memengaruhi FR-04 hingga FR-07 dan FR-12.
- Apakah diperlukan fitur save/load lokal; saat ini tidak dimasukkan karena tidak disebutkan dalam `01-overview.md`.