"""Twenty-four authored memory chapters: four acts with six puzzle families each."""

from echo_game.levels import Level, Rect
from .quests import QuestNode, QuestPlan

CHAPTERS = (
    ("KEBUN AMBANG", "garden", "relay", "Lampu di kebun padam bukan karena ditinggalkan. Seseorang menyimpan sumbunya untukmu."),
    ("SUMUR DESA", "canal", "valve", "Di dinding sumur, tinggi air dicatat setiap pagi. Tulisan berubah; kebiasaan merawat tidak."),
    ("MENARA LONCENG", "chapel", "tone", "Tiga nada memanggil orang pulang. Nama orangnya tak lagi tertulis, tetapi nadanya tetap sama."),
    ("BENGKEL PENJAGA", "workshop", "weight", "Penjaga memperbaiki pintu yang selalu rusak. Ia tidak menghitung berapa kali seseorang lupa menguncinya."),
    ("RUMAH KACA", "garden", "mirror", "Tanaman di sisi gelap tumbuh menuju pantulan, bukan menuju matahari. Harapan kadang mengambil jalan lain."),
    ("PERON TERAKHIR", "station", "circuit", "Tiket ini bertanggal kemarin. Di belakangnya tertulis: aku akan menunggumu, bukan jadwal kereta."),
    ("RUANG KELAS", "library", "relay", "Buku tulismu penuh jawaban yang dicoret. Di tepinya, seseorang menggambar rumah kecil."),
    ("ARSIP HUJAN", "canal", "valve", "Arsip mencatat banjir sebagai kehilangan. Di bawah angka-angka ada daftar orang yang diselamatkan."),
    ("PERPUSTAKAAN SUARA", "library", "tone", "Sebuah rekaman menyebut resep tiga sendok gula. Suara itu berhenti untuk tertawa, bukan untuk mengoreksi."),
    ("GUDANG SURAT", "workshop", "weight", "Surat paling berat bukan yang terpanjang. Hanya dua kata di amplop ini: sampai rumah."),
    ("OBSERVATORIUM", "observatory", "mirror", "Bintang-bintang tidak membentuk nama siapa pun. Kau boleh tetap mencari arah di antaranya."),
    ("RUANG SAMBUNG", "station", "circuit", "Kabel yang putus meninggalkan dua ujung. Memperbaikinya tidak membutuhkan kesalahan siapa pun."),
    ("HUTAN PENANDA", "forest", "relay", "Pita di pohon menandai jalan, bukan batas. Ada yang memasangnya agar kau bisa kembali."),
    ("KINCIR SUNGAI", "canal", "valve", "Kincir bergerak meski tak ada orang yang mengingat kapan ia dibangun. Air tetap mengantarnya."),
    ("KAPEL TANPA NAMA", "chapel", "tone", "Tak ada nama di bangku ini. Ada bekas dua orang duduk bersebelahan, saling menyisakan tempat."),
    ("JEMBATAN TIMBANG", "workshop", "weight", "Kau tidak perlu mengangkat seluruh masa lalu. Satu benda yang ditinggalkan cukup membuka jalan."),
    ("DANAU PANTUL", "observatory", "mirror", "Pantulan di danau bukan salinan sempurna. Ia tetap menunjukkan cahaya di seberang."),
    ("LENTARA HUTAN", "forest", "circuit", "Seseorang menyalakan tiga lampu pada malam yang berbeda. Kini semuanya menuntunmu ke arah yang sama."),
    ("HALAMAN PERAWAT", "garden", "relay", "Di halaman, perawat membetulkan syal seorang pengunjung. Ia tak menanyakan nama untuk bersikap hangat."),
    ("RUANG AIR HANGAT", "hospital", "valve", "Cangkir ini masih hangat. Merawat tidak selalu berarti menyembuhkan; kadang berarti hadir."),
    ("RUANG MUSIK", "chapel", "tone", "Melodi yang sama kembali lebih pelan. Kau tidak diminta menyelesaikannya, hanya mendengarkan."),
    ("LEMARI KENANGAN", "library", "weight", "Foto, resep, surat. Benda-benda itu bukan tes. Tak ada nilai buruk ketika sebuah nama tak kembali."),
    ("JENDELA PULANG", "hospital", "mirror", "Dari jendela terlihat rumah yang pertama. Sekarang kau tahu: pintunya dibuka dari dua sisi."),
    ("AMBANG CAHAYA", "home", "circuit", "Kau bukan penjaga semua nama. Kau adalah cahaya kecil yang masih bisa menemani seseorang pulang."),
)

VOCABULARY = {
    "relay": ("sumbu", "minyak", "kaca", "api"),
    "valve": ("1 aliran", "2 aliran", "3 aliran", "4 aliran"),
    "tone": ("DO", "MI", "SOL", "LA"),
    "weight": ("foto", "resep", "surat", "kunci"),
    "mirror": ("UTARA", "TIMUR", "SELATAN", "BARAT"),
    "circuit": (),
}
LAYOUTS = (
    (360, 900, 1450, 2200, 2650, 3100),
    (400, 2800, 1250, 2250, 800, 3100),
    (2750, 450, 1350, 850, 2350, 3050),
)


def build_journey(level_type, threat_type):
    rooms = []
    for index, (name, environment, family, story) in enumerate(CHAPTERS):
        act = index // 6
        choices = VOCABULARY[family]
        positions = LAYOUTS[(index // 6 + index % 6) % len(LAYOUTS)]
        if family == "weight":
            positions = LAYOUTS[0]  # Clear approaches for all three physical crates.
        targets = tuple((index + pair * 2 + act + 1) % 4 for pair in range(3))
        patterns = tuple(tuple((index + pair + n * (act + 1)) % 4 for n in range(3 + act)) for pair in range(3))
        nodes = []
        for pair, x in enumerate(positions[:3]):
            target = targets[pair]
            if family == "circuit":
                target = (index + pair * 2) % 7 + 1
                pattern = " / ".join("NYALA" if target & (1 << bit) else "MATI" for bit in range(3))
                clue = f"Catatan {pair + 1}: kiri / tengah / kanan = {pattern}."
            elif family == "weight":
                clue = f"Neraca {pair + 1}: tinggalkan peti di pelat di sebelah kiri neraca. Tubuhmu bukan pemberat."
            elif family == "valve":
                target = (index + pair * 2) % 7 + 1
                clue = f"Catatan air {pair + 1}: debit {target}. Cabang kiri / tengah / kanan memberi 1 / 2 / 4; jumlahkan alirannya."
            elif family == "mirror":
                clue = f"Peta cahaya {pair + 1}: pantulan harus menuju {choices[target]}."
            elif family == "tone":
                clue = f"Rekaman {pair + 1}: {' — '.join(choices[n] for n in patterns[pair])}. Bunyikan urutan ini dari awal di lonceng pasangan."
            else:
                clue = f"Label {pair + 1}: pasangan yang benar adalah {choices[target]}."
            nodes.append(QuestNode(x, f"CATATAN {pair + 1}", "source", clue + "\n" + story if pair == 0 else clue))
        for pair, x in enumerate(positions[3:]):
            kind = {"relay": "match", "valve": "valve", "tone": "melody", "weight": "weight",
                    "mirror": "dial", "circuit": "circuit"}[family]
            target = (index + pair * 2) % 7 + 1 if kind in ("circuit", "valve") else targets[pair]
            label = {"relay": "LENTERA", "valve": "KATUP", "tone": "LONCENG", "weight": "NERACA", "mirror": "CERMIN", "circuit": "RANGKAIAN"}[family]
            nodes.append(QuestNode(x, f"{label} {pair + 1}", kind,
                                   f"{label.title()} {pair + 1} tersambung. Sebuah bagian jalan pulang kembali.", target, choices,
                                   pattern=patterns[pair] if kind == "melody" else (),
                                   plate=(x - 105, 451, 130, 9) if kind == "weight" else None))
        # Music and optics let players collect all clues in one expedition;
        # repairs use alternating collection/delivery trips with a carried clue.
        order = (0, 1, 2, 3, 4, 5) if family in ("tone", "mirror") else (0, 3, 1, 4, 2, 5)
        plan = QuestPlan(family, story, tuple(nodes), order)
        # Several raised routes per chapter, with stairs rather than impossible
        # jumps. All clue stations stand on safe floor, not over instant deaths.
        terrain = [Rect(-80, 460, 3660, 160)]
        starts = (520, 1100, 1610) if family == "weight" else tuple(520 + n * 480 + act * 9 for n in range(5))
        for start in starts:
            if any(abs(start + 155 - x) < 200 for x in positions):
                continue
            terrain.extend((Rect(start, 410, 85, 18), Rect(start + 85, 360, 145, 18),
                            Rect(start + 230, 410, 85, 18)))
        crates = tuple((x - 240, 431, 58, 7 + pair) for pair, x in enumerate(positions[3:])) if family == "weight" else ()
        rooms.append(level_type(
            name,
            Level(f"{index + 5:02d} / {name}", story, "E: periksa/putar. J: jurnal. Ikuti kabel dan penanda catatan.",
                  3500, (130, 430), (3400, 430), tuple(terrain), crates=crates,
                  gate=Rect(3310, 250, 28, 210)),
            threats=(threat_type(1750, 425, 130, name, min(3, act)),),
            environment=environment, act=act + 2, quest=plan,
        ))
    return tuple(rooms)
