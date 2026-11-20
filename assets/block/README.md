# Block library

Greyscale plane-shape blocks generated with pycairo. Every category owns a
folder, and each folder holds three styles at 256x256 with a transparent
background:

| File | Look |
| --- | --- |
| `<kategori>_solid.png` | Shaded body, inner rim and diagonal light/shade sweep, dark outline |
| `<kategori>_flat.png` | Single grey fill with dark outline |
| `<kategori>_outline.png` | Hollow body with a thick grey frame and dark contour |

Categories: `persegi`, `segitiga`, `lingkaran`, `persegi-panjang`,
`jajar-genjang`, `belah-ketupat`, `layang-layang`, `trapesium`, `segi-lima`,
`segi-enam`, `segi-delapan`, `oval`, `setengah-lingkaran`, `bintang`.

`preview.png` is a contact sheet of all 42 sprites (shape columns, style rows).

## Runtime tinting

The source images contain only luminance (r = g = b), so a seeded RNG can pick
a colour and multiply it over the sprite without destroying the shading:

```python
import random
import pygame

PALETTE = [(196, 74, 62), (73, 128, 196), (92, 168, 96), (214, 170, 60)]

def tinted(path, rng):
    sprite = pygame.image.load(path).convert_alpha()
    tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
    tint.fill((*rng.choice(PALETTE), 255))
    sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return sprite
```

## Regenerating

```bash
.venv-echo/bin/python -m echo_game.generate_blocks --force
```

Add `--size 512` for larger output; the geometry scales with the canvas.
