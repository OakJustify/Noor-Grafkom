"""Standalone story data / real pixels; no Game fixture or save files."""
import importlib
from dataclasses import FrozenInstanceError

import pytest
import pygame


def catalog():
    try:
        return importlib.import_module("nur_game.cinematics.catalog")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Subtitle story catalog is missing: {exc}")


def test_catalog_faithfully_orders_script_without_early_diagnosis():
    story = catalog()
    assert tuple(story.SCENES) == tuple(f"CS{i:02}" for i in range(9))
    assert [s.duration for s in story.SCENES.values()] == [15, 25, 30, 35, 35, 40, 40, 12, 90]
    assert [s.kind for s in story.SCENES.values()] == ["opening", *(["memory"] * 6), "void", "realworld"]
    required = {
        "CS00": ["Ikuti jalan."],
        "CS01": ["Yang ini miring.", "Kepalamu juga dari tadi tidak bisa diam.", "Sudah?", "Sudah. Tasnya jangan ketinggalan.", "Nah, kan."],
        "CS02": ["Ini rumah kita.", "Pohonnya tinggi sekali.", "Biar kelihatan dari jauh. Kalau pulang, tinggal cari pohonnya.", "Ya sudah. Jangan ditutup kalender, nanti rumahnya hilang.", "Masih panas?", "Masih."],
        "CS03": ["Tadi... lewat sini.", "Bu, aku cari dari tadi.", "Pohonnya dipindah?", "Rumahnya lewat sini. Kita jalan bareng, ya?", "Dekat?", "Dekat."],
        "CS04": ["Geser sedikit. Pohonnya ikut, ya.", "Bu, lihat sini.", "Ini anak siapa?", "Sepertinya pernah ke sini."],
        "CS05": ["Sudah dimasukkan?", "Gulanya sudah. Tinggal diaduk.", "Yang ini?", "Sudah, Bu. Tehnya boleh dicoba dulu.", "Kamu bikin terlalu panas.", "Kita tunggu sebentar."],
        "CS06": ["Yang ini dibuka saja?", "Tidak usah. Nanti kamu tahu yang mana buatanmu.", "Anak saya belum pulang sekolah.", "Ibu sedang menunggu dia?", "Biasanya sudah sampai.", "Aku duduk di sini dulu, ya."],
        "CS07": ["Tadi ada rumah di sini."],
        "CS08": ["Pagi, Bu.", "Kamu siapa?", "Aku Dara, Bu. Anak Ibu.", "Dara masih kecil.", "Aku yang dulu Ibu antar sekolah.", "Boleh aku duduk di sini?", "Boleh.", "Ini pakai gula?", "Sedikit. Ibu mau coba?", "Masih panas.", "Kita tunggu.", "Kainnya mau dijahit?", "Tidak, Bu. Aku bawa saja."],
    }
    for key, lines in required.items():
        scene = story.SCENES[key]
        assert [c.text for c in scene.cues if c.text] == lines
        assert all(c.duration > 0 and c.shot for c in scene.cues)
        assert isinstance(scene.cues, tuple)
        assert "alzheimer" not in (scene.title + " ".join(c.text + c.speaker for c in scene.cues)).lower()
        if key != "CS08":
            assert all(c.speaker not in {"NUR", "DARA", "NUR MUDA", "DARA KECIL"} for c in scene.cues)
    assert len({c.shot for s in story.SCENES.values() for c in s.cues}) >= 20
    assert story.CLOSING_LINES == (
        "Nur hidup dengan penyakit Alzheimer.",
        "Dunia yang memudar dalam Noor adalah gambaran simbolis sebuah pengalaman kehilangan ingatan. Kisah Nur adalah fiksi dan tidak mewakili pengalaman setiap orang dengan Alzheimer.",
        "Kesulitan mengenali seseorang bukan berarti ia tidak lagi layak ditemani.",
    )
    with pytest.raises(FrozenInstanceError):
        story.SCENES["CS00"].title = "changed"
    with pytest.raises(FrozenInstanceError):
        story.SCENES["CS00"].cues[0].text = "changed"


def renderer(size=(960, 540)):
    try:
        module = importlib.import_module("nur_game.cinematics.renderer")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Original story illustrator is missing: {exc}")
    return module.StoryRenderer(size)


def test_each_script_shot_renders_original_non_card_illustrations():
    import hashlib

    story = catalog()
    artist = renderer()
    screen = pygame.Surface((960, 540))
    hashes = set()
    for scene in story.SCENES.values():
        if scene.kind == "void":
            continue
        for cue in scene.cues:
            assert artist.draw(screen, scene, cue, 0.5) is screen
            pixels = pygame.surfarray.array3d(screen)
            # The illustration fills the stage above the subtitle area.
            assert len({tuple(rgb) for rgb in pixels[::16, :370:16].reshape(-1, 3)}) >= 25
            hashes.add(hashlib.sha256(pygame.image.tobytes(screen.subsurface((0, 0, 960, 370)), "RGB")).hexdigest())
    assert len(hashes) >= 26, "Purpose-built shots should not all reuse a text card / one room"
    scene = story.SCENES["CS08"]
    artist.draw(screen, scene, scene.cues[-1], 0)
    # Nur and adult Dara have separate illustrated faces, not symbolic wisps.
    for rect in ((300, 100, 165, 165), (520, 110, 170, 165)):
        pixels = pygame.surfarray.array3d(screen.subsurface(rect))
        skin = (pixels[:, :, 0] > 185) & (pixels[:, :, 0] > pixels[:, :, 1] * 1.10) & (pixels[:, :, 1] > pixels[:, :, 2] * 1.08)
        assert skin.sum() > 1400, "Both humans need visible skin-toned faces and hands"


def test_fragment_objects_are_six_distinct_small_anchored_drawings():
    import hashlib

    audio_before = pygame.mixer.get_init()
    artist = renderer()
    images = set()
    for key in ("F01", "F02", "F03", "F04", "F05", "F06"):
        screen = pygame.Surface((200, 160), pygame.SRCALPHA)
        screen.fill((0, 0, 0, 0))
        artist.draw_fragment(screen, key, 100, 80)
        alpha = pygame.surfarray.array_alpha(screen)
        assert alpha.sum() > 90000
        assert not alpha[:45].any() and not alpha[155:].any()
        assert not alpha[:, :25].any() and not alpha[:, 135:].any()
        assert alpha[60:140, 40:120].any()
        images.add(hashlib.sha256(pygame.image.tobytes(screen, "RGBA")).hexdigest())
    assert len(images) == 6
    assert pygame.mixer.get_init() == audio_before, "The subtitle illustrator must not change audio playback state"


def test_void_fades_then_last_three_seconds_are_entirely_opaque_black():
    story = catalog()
    artist = renderer()
    scene = story.SCENES["CS07"]
    screen = pygame.Surface((960, 540), pygame.SRCALPHA)
    luminance = []
    for elapsed in (0, 4, 8.8):
        artist.draw(screen, scene, scene.cues[0], 0, scene_elapsed=elapsed)
        luminance.append(pygame.surfarray.array3d(screen).mean())
    assert luminance[0] > luminance[1] > luminance[2] > 0
    for elapsed in (9, 10, 11.999, 12, 20):
        for paused in (False, True):
            screen.fill((242, 13, 199, 10))
            artist.draw(screen, scene, scene.cues[0], 1, scene_elapsed=elapsed, paused=paused)
            assert not pygame.surfarray.array3d(screen).any(), "No subtitle, hint, lamp or hidden world pixel may survive"
            assert (pygame.surfarray.array_alpha(screen) == 255).all()
    # Cue-only callers still get the final blackout, without a scene clock.
    artist.draw(screen, scene, scene.cues[-1], 0)
    assert not pygame.surfarray.array3d(screen).any()


@pytest.mark.parametrize("size", [(960, 540), (640, 360), (480, 270)])
def test_longest_subtitle_wraps_legibly_inside_dark_panel_with_controls(size):
    story = catalog()
    artist = renderer(size)
    scene, cue = max(((s, c) for s in story.SCENES.values() for c in s.cues), key=lambda pair: len(pair[1].text))
    screen = pygame.Surface(size)
    artist.draw(screen, scene, cue, 1, paused=True)
    panel = artist.last_subtitle_panel
    assert panel and screen.get_rect().contains(panel)
    assert tuple(screen.get_at((panel.left + 5, panel.centery)))[:3] == (19, 29, 34)
    layout = artist.last_subtitle_layout
    assert " ".join(line for line, _ in layout).split() == cue.text.split()
    assert len(layout) >= 2
    for line, rect in layout:
        assert panel.contains(rect)
        assert rect.height >= 13
        pixels = pygame.surfarray.array3d(screen.subsurface(rect))
        assert (pixels.min(axis=2) > 210).sum() > 20, f"Subtitle line {line!r} must have visible light text"
    assert artist.last_hint_text == "Enter lanjut / Space jeda / Esc lewati"
    assert screen.get_rect().contains(artist.last_hint_rect)
    assert "JEDA" == artist.last_pause_text
    # Non-dialogue shots still expose the controls.
    artist.draw(screen, story.SCENES["CS00"], story.SCENES["CS00"].cues[0], 0)
    assert artist.last_hint_rect.width > 0


@pytest.mark.parametrize("page", [0, 1, 2])
def test_ending_shows_two_coloured_humans_with_complete_closing_card(page):
    story = catalog()
    artist = renderer()
    screen = pygame.Surface((960, 540))
    assert artist.draw_ending(screen, page, time=1) is screen
    assert " ".join(line for line, _ in artist.last_subtitle_layout).split() == story.CLOSING_LINES[page].split()
    assert screen.get_rect().contains(artist.last_subtitle_panel)
    assert all(artist.last_subtitle_panel.contains(rect) for _, rect in artist.last_subtitle_layout)
    assert artist.last_hint_text == "Enter lanjut / K fragmen / R baru / Esc menu"
    for rect in ((330, 115, 115, 115), (555, 135, 105, 115)):
        pixels = pygame.surfarray.array3d(screen.subsurface(rect))
        skin = (pixels[:, :, 0] > 185) & (pixels[:, :, 0] > pixels[:, :, 1] * 1.10) & (pixels[:, :, 1] > pixels[:, :, 2] * 1.08)
        assert skin.sum() > 1400


def test_capture_story_renderer_contact_sheet():
    from pathlib import Path

    story = catalog()
    artist = renderer()
    screen = pygame.Surface((960, 540))
    tiles = []
    indices = [2, 1, 3, 4, 4, 1, 2, 0, -1]
    for scene, index in zip(story.SCENES.values(), indices):
        cue = scene.cues[index]
        artist.draw(screen, scene, cue, 1, scene_elapsed=6 if scene.kind == "void" else 0)
        tiles.append((scene.key + " | " + scene.title, screen.copy()))
    artist.draw(screen, story.SCENES["CS07"], story.SCENES["CS07"].cues[-1], 0, scene_elapsed=9)
    tiles.append(("CS07 | 9-12 detik: hitam total", screen.copy()))
    for page in range(3):
        artist.draw_ending(screen, page)
        tiles.append((f"Penutup | {page + 1}", screen.copy()))
    screen.fill((31, 41, 44))
    pygame.font.init()
    font = pygame.font.Font(None, 28)
    for index, (key, name) in enumerate(zip(("F01", "F02", "F03", "F04", "F05", "F06"), ("pita", "cangkir", "kunci", "foto", "resep", "kain"))):
        artist.draw_fragment(screen, key, 90 + index * 154, 245)
        label = font.render(key + " " + name, True, (242, 221, 185))
        screen.blit(label, label.get_rect(center=(90 + index * 154, 322)))
    tiles.append(("Enam benda penghubung", screen.copy()))
    sheet = pygame.Surface((1440, 1500))
    sheet.fill((19, 29, 34))
    for index, (title, image) in enumerate(tiles):
        x, y = index % 3 * 480, index // 3 * 300
        sheet.blit(pygame.transform.smoothscale(image, (480, 270)), (x, y + 30))
        sheet.blit(font.render(title, True, (242, 221, 185)), (x + 8, y + 5))
    path = Path("D:/HermesAgent/cache/scratch/noor-story-renderer-sheet.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(path))
    assert pygame.image.load(str(path)).get_size() == (1440, 1500)


def test_ending_has_subtle_motion_without_changing_cached_story_illustration():
    artist = renderer()
    screen = pygame.Surface((960, 540))
    artist.draw_ending(screen, time=0)
    first = pygame.image.tobytes(screen, "RGB")
    artist.draw_ending(screen, time=1.5)
    second = pygame.image.tobytes(screen, "RGB")
    assert first != second, "Quiet real-world gestures must not be a completely static text card"
    artist.draw_ending(screen, time=0)
    assert pygame.image.tobytes(screen, "RGB") == first, "Animation must not paint into the cached illustration"


def test_subtitle_font_cache_survives_font_module_shutdown_and_reinitialization():
    artist = renderer()
    story = catalog()
    scene = story.SCENES['CS01']
    screen = pygame.Surface((960, 540))
    artist.draw(screen, scene, scene.cues[1], 0)
    pygame.font.quit()
    pygame.font.init()
    # A new ordinary font works; only a stale native cached handle is at risk.
    assert pygame.font.Font(None, 23).size('Enter')[0] > 0
    try:
        artist.draw(screen, scene, scene.cues[1], 0)
    except pygame.error as exc:
        pytest.fail(f'Subtitle fonts did not survive application restart: {exc}')
    assert artist.last_subtitle_layout[0][0] == 'Yang ini miring.'
