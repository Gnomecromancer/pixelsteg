# pixelsteg

Hide arbitrary data inside PNG images using LSB steganography. No cloud, no accounts — pure Python.

```
pip install pixelsteg
```

## Usage

```bash
# Check how much a PNG can hold
steg capacity photo.png

# Hide a file
steg hide secret.txt photo.png output.png

# Extract it
steg reveal output.png

# Write extracted data to a file
steg reveal output.png recovered.txt

# With a password (XOR encryption)
steg hide secret.txt photo.png output.png --password hunter2
steg reveal output.png --password hunter2

# Double capacity (2 bits per channel, slight quality loss)
steg hide secret.txt photo.png output.png --bits 2
steg reveal output.png --bits 2
```

## How it works

Each pixel in a PNG has R, G, B channels (0–255). This tool replaces the least significant bit(s) of each channel with bits from your payload. A 1-bit change per channel is imperceptible to the human eye — a pixel at value 200 becoming 201 is invisible.

A small header (8 bytes: 4 magic + 4 length) is written first, then the payload follows. Optional XOR encryption scrambles the payload before writing.

**Capacity:** ~3 bits per pixel at 1 bit/channel. A 1000×1000 image holds ~366 KB.

## Notes

- Output must be PNG (lossless). JPEG would destroy the hidden bits.
- Use `--bits 2` for double capacity; pixels can shift by up to 3 — still very hard to see, but technically detectable with steganalysis tools.
- The password is simple XOR — not cryptographically strong. Use it to obscure, not secure.
