# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for OpenAI image generation and editing using the `gpt-image-1` model. The project consists of two main scripts:
- `imagegen.py` - Full-featured CLI supporting generation, editing, and multi-image reference
- `imagegen2.py` - Simplified version focused on basic generation

## Development Environment

**Python Version**: 3.13.2 (via virtual environment in `venv/`)
**Key Dependencies**:
- `openai` (v1.76.0) - OpenAI Python SDK
- `python-dotenv` (v1.1.0) - Environment variable management  
- `pydantic` (v2.11.3) - Data validation

**Environment Setup**:
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install --upgrade openai python-dotenv pydantic
```

## Running the Tool

**Basic Usage**:
```bash
# Activate venv first
source venv/bin/activate

# Generate images
python imagegen.py "A white siamese cat wearing VR goggles"

# Generate with custom parameters
python imagegen.py "Jakarta skyline at dusk" --size 1536x1024 --quality high -n 2

# Edit existing image
python imagegen.py "Make the cat wear a party hat" --image input.png

# Edit with mask
python imagegen.py "Add stars to the sky" --image input.png --mask mask.png

# Edit with high input fidelity (preserve faces, logos, details)
python imagegen.py "Change the background to a beach" --image portrait.png --input-fidelity high
```

## Configuration

- **API Key**: Stored in `.env` file as `OPENAI_API_KEY`
- **Output**: Generated images saved as PNG files in the project root
- **Supported Resolutions**: `1024x1024`, `1024x1536`, `1536x1024`
- **Quality Options**: `high`, `medium`, `low` (for gpt-image-1), `standard` (for dall-e-2 editing only)
- **Input Fidelity**: `high` (for editing - preserves faces, logos, and fine details)

## Architecture Notes

**Core Components**:
- `imagegen.py:48-51` - OpenAI client initialization with error handling
- Image validation using file existence checks and format verification
- Multi-image support for reference-based generation (mask not supported in multi-image mode)
- Comprehensive error handling for API calls, file I/O, and validation

**Key Functions** (in imagegen.py):
- Image generation using `client.images.generate()`
- Image editing using `client.images.edit()` 
- Automatic model selection (gpt-image-1 for generation, gpt-image-1 or dall-e-2 for editing)
- Base64 encoding for API communication
- File validation and error reporting

## Web UI

**Flask Web Application**: `app.py` provides a modern web interface for the CLI functionality.

**Running the Web UI**:
```bash
# Install Flask if not already installed
python3 -m pip install flask

# Start the web server
python3 app.py
```

**Web UI Features**:
- **Generation Tab**: Create images from text prompts with customizable parameters
- **Edit Tab**: Upload images and edit them with prompts and optional masks
- **File Upload**: Supports PNG, JPG, JPEG, GIF, BMP, WEBP, HEIC formats
- **Image Preview**: View generated/edited images before downloading
- **Download**: Save images locally
- **Responsive Design**: Works on desktop and mobile devices

**Web UI Architecture**:
- `app.py` - Flask backend with API endpoints (`/generate`, `/edit`, `/download`, `/preview`)
- `templates/index.html` - Frontend interface with tabbed layout
- `uploads/` - Temporary storage for uploaded files
- `outputs/` - Generated and edited images storage

## Testing

**CLI Testing**:
1. Activate virtual environment: `source venv/bin/activate` (if venv works)
2. Run generation: `python imagegen.py "test prompt"`
3. Run editing: `python imagegen.py "edit prompt" --image input.png`

**Web UI Testing**:
1. Start server: `python3 app.py`
2. Open browser: `http://localhost:5000`
3. Test generation and editing workflows through web interface