"""Core LSB steganography logic."""

import struct
from PIL import Image

MAGIC = b"STEG"
HEADER_SIZE = 8  # 4 magic + 4 length


def _capacity(img: Image.Image, bits_per_channel: int = 1) -> int:
    """Max bytes that can be hidden in this image."""
    w, h = img.size
    total_bits = w * h * 3 * bits_per_channel
    return (total_bits // 8) - HEADER_SIZE


def _xor(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def hide(
    payload: bytes,
    img: Image.Image,
    bits_per_channel: int = 1,
    password: bytes = b"",
) -> Image.Image:
    """Return a new image with payload hidden in LSBs."""
    cap = _capacity(img, bits_per_channel)
    if len(payload) > cap:
        raise ValueError(
            f"Payload too large: {len(payload)} bytes, image holds {cap} bytes"
        )

    if password:
        payload = _xor(payload, password)

    header = MAGIC + struct.pack(">I", len(payload))
    data = header + payload

    # Flatten to a bit stream
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)

    out = img.copy().convert("RGB")
    pixels = out.load()
    w, h = out.size
    mask = (1 << bits_per_channel) - 1  # e.g. 0b01 or 0b11

    bit_idx = 0
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            channels = [r, g, b]
            changed = False
            for c in range(3):
                if bit_idx + bits_per_channel > len(bits):
                    break
                chunk = 0
                for _ in range(bits_per_channel):
                    chunk = (chunk << 1) | bits[bit_idx]
                    bit_idx += 1
                channels[c] = (channels[c] & ~mask) | chunk
                changed = True
            pixels[x, y] = tuple(channels)
            if not changed:
                break
        else:
            continue
        break

    return out


def reveal(
    img: Image.Image,
    bits_per_channel: int = 1,
    password: bytes = b"",
) -> bytes:
    """Extract hidden payload from image LSBs."""
    img = img.convert("RGB")
    pixels = img.load()
    w, h = img.size
    mask = (1 << bits_per_channel) - 1

    bits = []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            for ch in (r, g, b):
                val = ch & mask
                for shift in range(bits_per_channel - 1, -1, -1):
                    bits.append((val >> shift) & 1)

    def bits_to_bytes(bit_list: list) -> bytes:
        out = bytearray()
        for i in range(0, len(bit_list) - 7, 8):
            byte = 0
            for b in bit_list[i : i + 8]:
                byte = (byte << 1) | b
            out.append(byte)
        return bytes(out)

    raw = bits_to_bytes(bits)

    if len(raw) < HEADER_SIZE or raw[:4] != MAGIC:
        raise ValueError("No hidden data found (wrong image or wrong --bits value)")

    length = struct.unpack(">I", raw[4:8])[0]
    if length > len(raw) - HEADER_SIZE:
        raise ValueError("Corrupt header: declared length exceeds image capacity")

    payload = raw[HEADER_SIZE : HEADER_SIZE + length]

    if password:
        payload = _xor(payload, password)

    return payload
