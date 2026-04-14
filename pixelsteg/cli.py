"""CLI entry point for pixelsteg."""

import argparse
import sys
from pathlib import Path

from PIL import Image

from .core import hide, reveal, _capacity


def cmd_hide(args: argparse.Namespace) -> int:
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"error: payload file not found: {payload_path}", file=sys.stderr)
        return 1

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"error: image not found: {img_path}", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    if out_path.suffix.lower() != ".png":
        print("error: output must be a .png file", file=sys.stderr)
        return 1

    payload = payload_path.read_bytes()
    password = args.password.encode() if args.password else b""

    try:
        img = Image.open(img_path)
    except Exception as e:
        print(f"error: could not open image: {e}", file=sys.stderr)
        return 1

    cap = _capacity(img, args.bits)
    print(f"image capacity: {cap} bytes")
    print(f"payload size:   {len(payload)} bytes")

    if len(payload) > cap:
        print(
            f"error: payload too large by {len(payload) - cap} bytes", file=sys.stderr
        )
        return 1

    try:
        out_img = hide(payload, img, bits_per_channel=args.bits, password=password)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out_img.save(out_path, format="PNG")
    print(f"saved: {out_path}")
    return 0


def cmd_reveal(args: argparse.Namespace) -> int:
    img_path = Path(args.image)
    if not img_path.exists():
        print(f"error: image not found: {img_path}", file=sys.stderr)
        return 1

    password = args.password.encode() if args.password else b""

    try:
        img = Image.open(img_path)
    except Exception as e:
        print(f"error: could not open image: {e}", file=sys.stderr)
        return 1

    try:
        payload = reveal(img, bits_per_channel=args.bits, password=password)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.write_bytes(payload)
        print(f"extracted {len(payload)} bytes → {out_path}")
    else:
        # Try to print as text, fall back to hex preview
        try:
            text = payload.decode("utf-8")
            print(text, end="")
        except UnicodeDecodeError:
            preview = payload[:64].hex()
            print(f"binary data ({len(payload)} bytes): {preview}{'...' if len(payload) > 64 else ''}")

    return 0


def cmd_capacity(args: argparse.Namespace) -> int:
    img_path = Path(args.image)
    if not img_path.exists():
        print(f"error: image not found: {img_path}", file=sys.stderr)
        return 1

    try:
        img = Image.open(img_path)
    except Exception as e:
        print(f"error: could not open image: {e}", file=sys.stderr)
        return 1

    w, h = img.size
    for bits in (1, 2):
        cap = _capacity(img, bits)
        print(f"--bits {bits}: {cap:,} bytes  ({cap / 1024:.1f} KB)")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="steg",
        description="Hide and reveal data in PNG images using LSB steganography.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # hide
    p_hide = sub.add_parser("hide", help="Hide a file inside a PNG image")
    p_hide.add_argument("payload", help="File to hide")
    p_hide.add_argument("image", help="Cover image (PNG, JPEG, etc.)")
    p_hide.add_argument("output", help="Output PNG path")
    p_hide.add_argument(
        "--bits",
        type=int,
        choices=[1, 2],
        default=1,
        help="Bits per channel (1=imperceptible, 2=double capacity; default: 1)",
    )
    p_hide.add_argument("--password", "-p", help="XOR encrypt payload with this key")

    # reveal
    p_reveal = sub.add_parser("reveal", help="Extract hidden data from a PNG image")
    p_reveal.add_argument("image", help="Stego image")
    p_reveal.add_argument("output", nargs="?", help="Write extracted data to this file (default: stdout)")
    p_reveal.add_argument(
        "--bits",
        type=int,
        choices=[1, 2],
        default=1,
        help="Bits per channel used when hiding (default: 1)",
    )
    p_reveal.add_argument("--password", "-p", help="Decryption key (must match hide)")

    # capacity
    p_cap = sub.add_parser("capacity", help="Show how much data an image can hold")
    p_cap.add_argument("image", help="Image to inspect")

    args = parser.parse_args()

    if args.command == "hide":
        return cmd_hide(args)
    elif args.command == "reveal":
        return cmd_reveal(args)
    elif args.command == "capacity":
        return cmd_capacity(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
