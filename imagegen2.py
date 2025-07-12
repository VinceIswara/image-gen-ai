#!/usr/bin/env python3
"""
Quick test script for OpenAI's gpt-image-1 generation endpoint.

Prerequisites
-------------
1. Install the official OpenAI Python SDK 1.x:

    pip install --upgrade openai

2. Export your API key in the shell that will run this script:

    export OPENAI_API_KEY="sk-..."

Usage examples
--------------
# Basic usage – generates a single 1024 × 1024 image and prints the URL
python imagegen.py "A white siamese cat wearing VR goggles"

# Custom size, better quality, request 2 variants
python imagegen.py "Jakarta skyline at dusk in cyber‑punk style" --size 1536x1024 --quality high -n 2
"""

import argparse
import base64
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env so OPENAI_API_KEY is available
from openai import OpenAI

def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "high",
    n: int = 1,
) -> list[bytes]:
    """
    Generate one or more images using OpenAI gpt-image-1 and return them as raw PNG bytes.

    Parameters
    ----------
    prompt : str
        The text prompt describing the desired image.
    size : str, optional
        Image resolution such as "1024x1024", "1536x1024", "1024x1536". Default "1024x1024".
    quality : str, optional
        "high", "medium", or "low". Higher quality is slower/more expensive. Default "high".
    n : int, optional
        Number of images to generate (1‑10). Default 1.

    moderation : str, optional
        Content‑moderation strictness; this script uses "low" by default.

    Returns
    -------
    list[bytes]
        A list of PNG image bytes for each generated image.
    """
    client = OpenAI()  # Uses OPENAI_API_KEY from environment
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        quality=quality,
        n=n,
        moderation="low",
    )
    return [base64.b64decode(d.b64_json) for d in response.data]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="imagegen.py",
        description="Quick test for OpenAI image generation (gpt-image-1).",
    )
    parser.add_argument("prompt", nargs="+", help="Text prompt that describes the desired image.")
    parser.add_argument("--size", default="1024x1024", help='Image size, e.g. "1024x1024" or "1536x1024" or "1024x1536".')
    parser.add_argument(
        "--quality",
        default="high",
        choices=["high", "medium", "low"],
        help="Generation quality; 'high' gives sharper results but costs more.",
    )
    parser.add_argument(
        "-n", "--num", type=int, default=1, help="Number of images to create (max 10)."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = " ".join(args.prompt)
    images = generate_image(prompt, size=args.size, quality=args.quality, n=args.num)

    for idx, img_bytes in enumerate(images, start=1):
        fname = f"output{'_' + str(idx) if len(images) > 1 else ''}.png"
        with open(fname, "wb") as f:
            f.write(img_bytes)
        print(f"Saved {fname}")


if __name__ == "__main__":
    main()