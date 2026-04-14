"""Tests for pixelsteg core logic."""

import pytest
from PIL import Image

from pixelsteg.core import hide, reveal, _capacity, MAGIC


def make_image(w: int = 100, h: int = 100) -> Image.Image:
    """Create a solid grey test image."""
    img = Image.new("RGB", (w, h), color=(128, 128, 128))
    return img


def make_noisy_image(w: int = 100, h: int = 100) -> Image.Image:
    """Create an image with varied pixel values."""
    import random
    rng = random.Random(42)
    img = Image.new("RGB", (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            pixels[x, y] = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    return img


# --- capacity ---

def test_capacity_1bit():
    img = make_image(100, 100)
    cap = _capacity(img, bits_per_channel=1)
    # 100*100*3*1 bits = 30000 bits = 3750 bytes, minus 8 header = 3742
    assert cap == 3742


def test_capacity_2bit():
    img = make_image(100, 100)
    cap = _capacity(img, bits_per_channel=2)
    # 100*100*3*2 bits = 60000 bits = 7500 bytes, minus 8 header = 7492
    assert cap == 7492


# --- hide / reveal roundtrip ---

def test_roundtrip_text():
    img = make_image()
    payload = b"hello, world!"
    out = hide(payload, img)
    assert reveal(out) == payload


def test_roundtrip_binary():
    img = make_image()
    payload = bytes(range(256))
    out = hide(payload, img)
    assert reveal(out) == payload


def test_roundtrip_empty():
    img = make_image()
    payload = b""
    out = hide(payload, img)
    assert reveal(out) == payload


def test_roundtrip_large():
    img = make_image(200, 200)
    payload = b"x" * 3000
    out = hide(payload, img)
    assert reveal(out) == payload


def test_roundtrip_2bits():
    img = make_image()
    payload = b"two bits per channel"
    out = hide(payload, img, bits_per_channel=2)
    assert reveal(out, bits_per_channel=2) == payload


def test_roundtrip_noisy_image():
    img = make_noisy_image()
    payload = b"hidden in noise"
    out = hide(payload, img)
    assert reveal(out) == payload


# --- password / XOR ---

def test_password_roundtrip():
    img = make_image()
    payload = b"secret message"
    password = b"hunter2"
    out = hide(payload, img, password=password)
    assert reveal(out, password=password) == payload


def test_password_wrong_key_gives_garbage():
    img = make_image()
    payload = b"secret message"
    out = hide(payload, img, password=b"correctkey")
    result = reveal(out, password=b"wrongkey")
    assert result != payload


def test_no_password_vs_password():
    img = make_image()
    payload = b"test"
    out_plain = hide(payload, img)
    out_encrypted = hide(payload, img, password=b"key")
    # The stego images should differ (different bits written)
    plain_pixels = list(out_plain.getdata())
    enc_pixels = list(out_encrypted.getdata())
    assert plain_pixels != enc_pixels


# --- error cases ---

def test_payload_too_large():
    img = make_image(10, 10)  # tiny image
    payload = b"x" * 10000
    with pytest.raises(ValueError, match="too large"):
        hide(payload, img)


def test_reveal_no_data():
    img = make_image()
    # Fresh image has no magic header
    with pytest.raises(ValueError, match="No hidden data"):
        reveal(img)


def test_reveal_wrong_bits():
    img = make_image()
    payload = b"bits mismatch test"
    out = hide(payload, img, bits_per_channel=1)
    # Trying to read with wrong bits_per_channel should fail
    with pytest.raises(ValueError):
        reveal(out, bits_per_channel=2)


# --- image integrity ---

def test_output_is_png_rgb():
    img = make_image()
    out = hide(b"test", img)
    assert out.mode == "RGB"


def test_pixel_delta_1bit():
    """LSB hiding should change pixels by at most 1 per channel."""
    img = make_noisy_image(50, 50)
    payload = b"delta check"
    out = hide(payload, img)

    orig_pixels = list(img.convert("RGB").getdata())
    out_pixels = list(out.getdata())

    for (or_, og, ob), (nr, ng, nb) in zip(orig_pixels, out_pixels):
        assert abs(or_ - nr) <= 1
        assert abs(og - ng) <= 1
        assert abs(ob - nb) <= 1


def test_pixel_delta_2bits():
    """2-bit hiding should change pixels by at most 3 per channel."""
    img = make_noisy_image(50, 50)
    payload = b"delta check 2bit"
    out = hide(payload, img, bits_per_channel=2)

    orig_pixels = list(img.convert("RGB").getdata())
    out_pixels = list(out.getdata())

    for (or_, og, ob), (nr, ng, nb) in zip(orig_pixels, out_pixels):
        assert abs(or_ - nr) <= 3
        assert abs(og - ng) <= 3
        assert abs(ob - nb) <= 3


# --- reproducibility ---

def test_deterministic():
    img = make_image()
    payload = b"same input"
    out1 = hide(payload, img)
    out2 = hide(payload, img)
    assert list(out1.getdata()) == list(out2.getdata())
