"""Create the mod's texture atlas from the recipient's Minecraft installation."""
import io
import struct
import zipfile
from PIL import Image
from patch_ops import sha256


def make_textures(jar, required):
    with zipfile.ZipFile(jar) as archive:
        images = {}
        for label, spec in required.items():
            blob = archive.read(spec['path'])
            if sha256(blob) != spec['sha256']:
                raise ValueError('Minecraft textures do not match this release. Install Java 1.21.11 through your launcher.')
            images[label] = Image.open(io.BytesIO(blob)).convert('RGBA')
    atlas = Image.new('RGBA', (128, 128), (110, 78, 44, 255))
    atlas.paste(images['steve'], (0, 0))
    atlas.paste(images['shield'], (64, 0))
    atlas.paste(images['sword'], (0, 64))
    layers = [atlas.resize((1024, 1024), Image.Resampling.NEAREST),
              Image.new('RGBA', (64, 64), (128, 128, 255, 255)),
              Image.new('RGBA', (64, 64), (0, 0, 0, 255))]
    blobs = []
    for layer in layers:
        stream = io.BytesIO()
        layer.save(stream, format='DDS', pixel_format='DXT5')
        blobs.append(stream.getvalue())
    wta = bytearray(struct.pack('<4s7I', b'WTB\0', 3, 3, 32, 64, 96, 128, 0))
    tables = [[sum(len(x) for x in blobs[:i]) for i in range(3)],
              [len(x) for x in blobs], [0x26000020, 0x22000020, 0x22000020],
              [0x4d435301, 0x4d435302, 0x4d435303]]
    for table in tables:
        wta.extend(struct.pack('<8I', *(table + [0] * 5)))
    return bytes(wta), b''.join(blobs)
