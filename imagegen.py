#!/usr/bin/env python3
"""
Quick test script for OpenAI image generation (gpt-image-1)
and editing (gpt-image-1 or dall-e-2).

Prerequisites
-------------
1. Install the official OpenAI Python SDK 1.x:

    pip install --upgrade openai python-dotenv

2. Create a .env file in the same directory with your key:
   OPENAI_API_KEY="sk-..."
   (Or export OPENAI_API_KEY="sk-...")

Usage examples
--------------
# Generation: Generate a single 1024x1024 image
python imagegen.py "A white siamese cat wearing VR goggles"

# Generation: Custom size, better quality, request 2 variants
python imagegen.py "Jakarta skyline at dusk in cyber‑punk style" --size 1536x1024 --quality high -n 2

# Editing (Single Image): Edit 'input.png' based on a prompt
python imagegen.py "Make the cat wear a party hat" --image input.png

# Editing (Single Image with Mask): Edit 'input.png' in areas specified by 'mask.png'
python imagegen.py "Add stars to the sky" --image input.png --mask mask.png --size 1024x1024 -n 1

# Editing (High Fidelity): Edit with high fidelity to preserve faces, logos, and details
python imagegen.py "Change the background to a beach" --image portrait.png --input-fidelity high

# Editing (Multiple Reference Images): Generate based on prompt using multiple reference images
# (Note: Mask is not supported in multi-image mode)
python imagegen.py "Create a gift basket with these items" --image item1.png item2.png item3.png
"""

import argparse
import base64
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env so OPENAI_API_KEY is available
import os
import re
from openai import OpenAI, APIError, APIConnectionError, APIStatusError
from contextlib import ExitStack # Needed for safely opening multiple files
import sys # For stderr and exit

# Initialize OpenAI client globally (uses OPENAI_API_KEY from environment)
# Handle potential error if key is missing
try:
    client = OpenAI()
except APIError as e:
    print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
    print("Please ensure OPENAI_API_KEY is set in your environment or .env file.", file=sys.stderr)
    sys.exit(1)


def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "high",
    n: int = 1,
    moderation: str = "low",
) -> list[bytes] | None:
    """
    Generate one or more images using OpenAI gpt-image-1.

    Parameters refer to the 'images.generate' endpoint documentation.
    Note: 'moderation' is specific to generate.
    """
    allowed_sizes = {"1024x1024", "1024x1536", "1536x1024"}
    if size not in allowed_sizes:
        print(
            f"Error: Size '{size}' is not supported by gpt-image-1. "
            f"Supported sizes: {', '.join(sorted(allowed_sizes))}.",
            file=sys.stderr
        )
        return None

    print(f"Generating image with model gpt-image-1...")
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
            moderation=moderation, # Supported by gpt-image-1 generate
            # response_format removed as it's not supported by gpt-image-1 generate
        )
        print("Image generation complete.")
        return [base64.b64decode(d.b64_json) for d in response.data]
    except (APIError, APIConnectionError, APIStatusError) as e:
        print(f"\nError during image generation: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        return None

def edit_image(
    prompt: str,
    image_paths: list[str], # Changed from image_path: str to list[str]
    mask_path: str | None = None,
    size: str = "1024x1024",
    quality: str = "high", # Note: DALL-E 2 only supports 'standard'
    n: int = 1,
    model: str = "gpt-image-1", # Can be "dall-e-2" as well for edits
    input_fidelity: str | None = None # New parameter for high-fidelity preservation
) -> list[bytes] | None:
    """
    Edit an image or generate based on reference images using OpenAI gpt-image-1 or dall-e-2.

    Parameters refer to the 'images.edit' endpoint documentation.
    Accepts one or more image paths. Mask is only used if exactly one image path is provided.
    """
    if not image_paths:
        print("Error: No image paths provided for editing.", file=sys.stderr)
        return None

    # Input validation specific to multi-image vs single-image+mask
    is_multi_image = len(image_paths) > 1
    effective_mask_path = mask_path # Use a temporary variable
    if is_multi_image and effective_mask_path:
        print("Warning: Mask is ignored when multiple input images are provided.", file=sys.stderr)
        effective_mask_path = None # Don't use mask in multi-image mode

    image_basenames = ', '.join([os.path.basename(p) for p in image_paths])
    print(f"Editing based on image(s) '{image_basenames}' with model {model}...")

    if model == "gpt-image-1":
        allowed_sizes = {"1024x1024", "1024x1536", "1536x1024"}
        if size not in allowed_sizes:
            print(
                f"Error: Size '{size}' is not supported by gpt-image-1. "
                f"Supported sizes: {', '.join(sorted(allowed_sizes))}.",
                file=sys.stderr
            )
            return None
    elif model == "dall-e-2":
         # DALL-E 2 edit might not support multiple input images, needs verification
         if is_multi_image:
              print(f"Warning: Using multiple images with dall-e-2 edit is experimental/unverified.", file=sys.stderr)
         if quality != "standard":
              print(f"Warning: Quality '{quality}' ignored. DALL-E 2 only supports 'standard'.", file=sys.stderr)
              quality = "standard"


    opened_mask_file = None
    opened_image_files = []

    try:
        # Use ExitStack to safely manage opening multiple files
        with ExitStack() as stack:
            # Open all image files
            for path in image_paths:
                file_obj = stack.enter_context(open(path, "rb"))
                opened_image_files.append(file_obj)

            # Open mask file only if path is provided and it's not multi-image mode
            if effective_mask_path:
                print(f"Using mask '{os.path.basename(effective_mask_path)}'")
                opened_mask_file = stack.enter_context(open(effective_mask_path, "rb"))

            # --- Prepare Parameters and Make the API Call ---
            api_params = {
                "model": model,
                "image": opened_image_files, # Pass the list of opened file objects
                "prompt": prompt,
                "n": n,
                "size": size,
                "quality": quality if model == "gpt-image-1" else "standard",
            }
            # Conditionally add the mask parameter ONLY if an opened mask file exists
            if opened_mask_file:
                api_params["mask"] = opened_mask_file
            # Conditionally add input_fidelity parameter if specified
            if input_fidelity:
                api_params["input_fidelity"] = input_fidelity

            # Make the call using dictionary unpacking
            response = client.images.edit(**api_params)
            # -------------------------------------------------

        print("Image editing/generation complete.")

        # Process response
        if response.data and response.data[0].b64_json:
            return [base64.b64decode(d.b64_json) for d in response.data]
        elif response.data and response.data[0].url:
            # Handle URL case if needed in the future (e.g., download the image)
            print("Received URL instead of b64_json (likely DALL-E 2 default). Returning None.", file=sys.stderr)
            print("URLs:", [d.url for d in response.data])
            return None
        else:
            print("Warning: Received unexpected response format.", file=sys.stderr)
            return None

    except FileNotFoundError as e:
        print(f"\nError: Input file not found - {e}", file=sys.stderr)
        return None
    except (APIError, APIConnectionError, APIStatusError) as e:
        print(f"\nError during image editing/generation: {e}", file=sys.stderr)
        # You might want to check e.body for more specific error details from OpenAI
        if hasattr(e, 'body') and e.body:
            print(f"API Error Body: {e.body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred during file handling or API call: {e}", file=sys.stderr)
        return None
    # ExitStack ensures files are closed automatically here, even if errors occurred


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="imagegen.py",
        description="Generate or edit images using OpenAI (gpt-image-1 or dall-e-2).",
        formatter_class=argparse.RawTextHelpFormatter # Keep formatting in help
    )
    parser.add_argument("prompt", nargs="+", help="Text prompt describing the desired image or edit.")

    # --- Image Generation/Editing Arguments ---
    parser.add_argument(
        "--image", "-i", type=str, default=None, nargs='+', # Changed nargs to '+'
        help="Path(s) to the input image file(s) for editing or reference. \n"
             "If provided, activates edit mode. Multiple images act as references \n"
             "(mask is ignored in this case)."
    )
    parser.add_argument(
        "--mask", "-m", type=str, default=None,
        help="Path to the mask file (PNG) for editing specific areas. \n"
             "Requires --image (and only works with a single --image).\n"
             "Transparent areas in the mask indicate where the image should be edited."
    )
    # Model selection (kept commented out as in original)
    # parser.add_argument("--model", default="gpt-image-1", choices=["gpt-image-1", "dall-e-2"],
    #                     help="Model to use ('gpt-image-1' for generate/edit, 'dall-e-2' for edit only).")

    # --- Common Arguments ---
    parser.add_argument(
        "--size", default="1024x1024",
        help='Image size. Examples:\n'
             '- For gpt-image-1: "1024x1024", "1536x1024", "1024x1536"\n'
             '- For dall-e-2 (edit only): "256x256", "512x512", "1024x1024"'
    )
    parser.add_argument(
        "--quality", default="high", choices=["high", "medium", "low", "standard"], # Added 'standard'
        help="Generation/edit quality:\n"
             "- 'high', 'medium', 'low' (gpt-image-1)\n"
             "- 'standard' (dall-e-2 edit only)"
    )
    parser.add_argument(
        "--moderation", default="low", choices=["auto", "low"],
        help="Content filtering level for generation/edit"
    )
    parser.add_argument(
        "--input-fidelity", default=None, choices=["high"],
        help="Input fidelity level for editing (high = preserve faces, logos, and details)"
    )
    parser.add_argument(
        "-n", "--num", type=int, default=1,
        help="Number of images to create (max 10)."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = " ".join(args.prompt)
    images = None # Initialize images to None

    # Decide whether to generate or edit based on --image argument
    if args.image: # args.image is now a list of paths if provided
        # --- Edit Mode ---

        # Validate all image paths exist
        for img_path in args.image:
            if not os.path.exists(img_path):
                 print(f"Error: Image file not found at '{img_path}'", file=sys.stderr)
                 sys.exit(1)

        # Validate mask path exists if provided
        if args.mask and not os.path.exists(args.mask):
             print(f"Error: Mask file not found at '{args.mask}'", file=sys.stderr)
             sys.exit(1)

        # Explicitly prevent mask with multiple images *before* calling edit_image
        # (edit_image also has a check, but better to fail early)
        if len(args.image) > 1 and args.mask:
            print("Error: Providing a mask (--mask) is not supported when multiple input images (--image) are specified.", file=sys.stderr)
            print("Please provide only one --image if you need to use a --mask.")
            sys.exit(1)

        # Assume gpt-image-1 for edits for now, consistent with script's focus
        # Could use args.model if that argument was enabled
        images = edit_image(
            prompt=prompt,
            image_paths=args.image, # Pass the list of paths
            mask_path=args.mask,   # Pass mask path (will be ignored if len(args.image) > 1)
            size=args.size,
            quality=args.quality, # Pass user choice, function handles model compatibility
            n=args.num,
            model="gpt-image-1", # Hardcoded for now
            input_fidelity=args.input_fidelity # Pass input fidelity parameter
        )
    else:
        # --- Generate Mode ---
        if args.mask:
            print("Warning: --mask argument ignored when not in edit mode (no --image provided).", file=sys.stderr)
        images = generate_image(
            prompt=prompt,
            size=args.size,
            quality=args.quality,
            n=args.num,
            moderation=args.moderation,
        )

    # --- Save Results (if any) ---
    if images:
        output_prefix = "edited" if args.image else "output"
        sanitized_prompt = re.sub(r"[^A-Za-z0-9._-]", "_", prompt)
        base_filename = f"{output_prefix}_{sanitized_prompt[:40]}"

        print("-" * 20)
        for idx, img_bytes in enumerate(images, start=1):
            num_suffix = f"_{idx}" if args.num > 1 else ""
            fname = f"{base_filename}{num_suffix}.png"
            try:
                with open(fname, "wb") as f:
                    f.write(img_bytes)
                print(f"Saved {fname}")
            except IOError as e:
                print(f"Error saving file {fname}: {e}", file=sys.stderr)
        print("-" * 20)
    else:
        print("No images were generated or edited successfully.")


if __name__ == "__main__":
    main()