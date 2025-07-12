# 🎨 AI Image Studio

A powerful tool for OpenAI image generation and editing with both **command-line** and **web interface** options using the **`gpt-image-1`** model.

---

## ✨ Features

### 🖥️ **Web Interface** (New!)
* **Modern web UI** with tabbed interface for generation and editing
* **Drag-and-drop file upload** for images and masks
* **Live image preview** with full-size modal viewing
* **Real-time generation** with loading indicators
* **Download management** with one-click saves
* **Responsive design** for desktop and mobile

### 💻 **Command Line Interface**
* **Generate** 1‑10 images from text prompts
* **Edit** existing images with or without masks
* **Multiple reference images** for generation context
* **Flexible parameters** for size, quality, and quantity

### 🎛️ **Supported Options**
* **Resolutions**: `1024x1024`, `1024x1536`, `1536x1024`
* **Quality tiers**: `high`, `medium`, `low` (+ `standard` for dall-e-2 editing)
* **Moderation levels**: `low` (default) or `auto`
* **Batch generation**: 1-10 images per request

> **Note**  
> Supports both image generation (gpt-image-1) and editing (gpt-image-1 or dall-e-2)

---

## 📋 Requirements

```bash
python >= 3.9
pip install --upgrade openai python-dotenv flask
```

**Dependencies:**
- [`openai`](https://pypi.org/project/openai/) - Official OpenAI Python SDK
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) - Environment variable management
- [`flask`](https://pypi.org/project/flask/) - Web framework for the UI (optional for CLI-only usage)

---

## 🔑 Setup

1. Clone or copy the repo.  
2. Create a file named `.env` in the project root:

```env
OPENAI_API_KEY="sk-…"   # keep this secret and never commit it!
```

That's it—the script automatically loads the file via `load_dotenv()`.

---

## 🚀 Usage

### 🖥️ **Web Interface** (Recommended)

Start the web server:
```bash
python3 app.py
```

Then open your browser to: **`http://localhost:5001`**

**Web Features:**
- **Generation Tab**: Enter prompts and customize settings
- **Edit Tab**: Upload images and masks for editing
- **Click images** to view full-size in modal
- **Download** generated images with one click
- **Responsive** interface works on all devices

### 💻 **Command Line Interface**

#### Basic Generation
```bash
python imagegen.py "A white siamese cat wearing VR goggles"
```

#### Custom size, better quality, multiple images
```bash
python imagegen.py "Jakarta skyline at dusk in cyber‑punk style" --size 1536x1024 --quality high -n 2
```

#### Image Editing
```bash
python imagegen.py "Make the cat wear a party hat" --image input.png
```

#### Image Editing with Mask
```bash
python imagegen.py "Add stars to the sky" --image input.png --mask mask.png --size 1024x1024 -n 1
```

### CLI options

| Flag / Option        | Description                                              |
|----------------------|----------------------------------------------------------|
| positional `prompt`  | Text describing the image you want to generate or the edit to apply. |
| `--image`, `-i`      | Path to the input image file for editing. If provided, activates edit mode. |
| `--mask`, `-m`       | Path to the mask file (PNG) for editing specific areas. Requires --image. Transparent areas in the mask indicate where the image should be edited. |
| `--size`             | Resolution as `WIDTHxHEIGHT`; default `1024x1024`.       |
| `--quality`          | `high` (default), `medium`, `low` — or `standard` **only when editing with `dall-e-2`** |
| `--moderation`       | `low` (default here) or `auto` – content‑filtering strictness. |
| `-n`, `--num`        | How many images to create (1‑10); default `1`.           |

---

## 🔌 How it works

### Architecture
- **`imagegen.py`** - Full-featured CLI with generation and editing
- **`imagegen2.py`** - Simplified CLI for basic generation
- **`app.py`** - Flask web server with REST API endpoints
- **`templates/index.html`** - Modern responsive web interface

### API Integration
Both CLI and web interface use the OpenAI Images API:

**Generation:**
```python
response = client.images.generate(
    model="gpt-image-1",
    prompt=prompt,
    size=size,
    quality=quality,
    n=n,
    moderation="low",
)
```

**Editing:**
```python
response = client.images.edit(
    model=model,  # "gpt-image-1" or "dall-e-2"
    image=image_file,
    mask=mask_file,  # Optional
    prompt=prompt,
    n=n,
    size=size,
    quality=quality,
)
```

For full parameter details see the [OpenAI Images API docs](https://platform.openai.com/docs/api-reference/images).

---

## 💸 Cost & limits

* **Quality tier** affects both cost and latency.  
* Account‑level rate limits still apply—check your dashboard.  
* Always protect your API key (use `.env`, environment variables, or a secrets manager).

---

## 📝 License

MIT—do whatever you like, just don't publish your real API key.
