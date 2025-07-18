#!/usr/bin/env python3
"""
Flask Web UI for OpenAI Image Generation and Editing
Provides a web interface for the CLI functionality in imagegen.py
"""

import os
import base64
import tempfile
import uuid
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, APIStatusError
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Create uploads and outputs directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Initialize OpenAI client
try:
    client = OpenAI()
except APIError as e:
    print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
    sys.exit(1)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/generate', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        size = data.get('size', '1024x1024')
        quality = data.get('quality', 'high')
        n = int(data.get('n', 1))
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Validate parameters
        valid_sizes = ['1024x1024', '1024x1536', '1536x1024', 'auto']
        valid_qualities = ['high', 'medium', 'low', 'standard']
        
        # Map 'auto' to default size for now
        if size == 'auto':
            size = '1024x1024'
        
        if size not in valid_sizes:
            return jsonify({'error': f'Size must be one of: {valid_sizes}'}), 400
        
        if quality not in valid_qualities:
            return jsonify({'error': f'Quality must be one of: {valid_qualities}'}), 400
        
        if n < 1 or n > 10:
            return jsonify({'error': 'Number of images must be between 1 and 10'}), 400
        
        # Generate image
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
            moderation="low"
        )
        
        # Save generated images
        image_urls = []
        for i, image_data in enumerate(response.data):
            # Generate unique filename
            filename = f"generated_{uuid.uuid4().hex}_{i}.png"
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            
            # Download and save image
            image_bytes = base64.b64decode(image_data.b64_json)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            image_urls.append(f'/download/{filename}')
        
        return jsonify({
            'success': True,
            'images': image_urls,
            'prompt': prompt,
            'parameters': {
                'size': size,
                'quality': quality,
                'count': n
            }
        })
        
    except APIError as e:
        return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/edit', methods=['POST'])
def edit_image():
    try:
        # Check if image file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'Image file is required'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF'}), 400
        
        # Get form data
        prompt = request.form.get('prompt', '').strip()
        size = request.form.get('size', '1024x1024')
        quality = request.form.get('quality', 'high')
        
        # Wrap int conversion in try/except to handle non-numeric input
        try:
            n = int(request.form.get('n', 1))
        except ValueError:
            return jsonify({'error': 'Number of images must be a valid integer'}), 400
            
        input_fidelity = request.form.get('input_fidelity', None)
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Validate parameters
        valid_sizes = ['1024x1024', '1024x1536', '1536x1024']
        valid_qualities = ['high', 'medium', 'low', 'auto']
        
        if size not in valid_sizes:
            return jsonify({'error': f'Size must be one of: {valid_sizes}'}), 400
        
        if quality not in valid_qualities:
            return jsonify({'error': f'Quality must be one of: {valid_qualities}'}), 400
        
        if n < 1 or n > 10:
            return jsonify({'error': 'Number of images must be between 1 and 10'}), 400
        
        # Open files for API call
        temp_filepath = None
        mask_filepath = None
        resp = None
        
        try:
            # Save uploaded image
            filename = secure_filename(image_file.filename)
            temp_filename = f"temp_{uuid.uuid4().hex}_{filename}"
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            image_file.save(temp_filepath)
            
            # Handle mask file if provided
            if 'mask' in request.files and request.files['mask'].filename != '':
                mask_file = request.files['mask']
                if not allowed_file(mask_file.filename):
                    return jsonify({'error': 'Invalid mask file type. Allowed: PNG, JPG, JPEG, GIF'}), 400
                
                mask_filename = secure_filename(mask_file.filename)
                temp_mask_filename = f"mask_{uuid.uuid4().hex}_{mask_filename}"
                mask_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_mask_filename)
                mask_file.save(mask_filepath)
            
            with open(temp_filepath, 'rb') as img_file:
                mask_file_obj = None
                if mask_filepath:
                    mask_file_obj = open(mask_filepath, 'rb')
                
                try:
                    # Edit image
                    edit_params = {
                        "model": "gpt-image-1",
                        "image": img_file,
                        "prompt": prompt,
                        "n": n,
                        "size": size,
                        "quality": quality,
                        }
                    
                    # Add optional parameters
                    if mask_file_obj:
                        edit_params["mask"] = mask_file_obj
                    if input_fidelity in ("low", "high"):
                        edit_params["input_fidelity"] = input_fidelity
                    
                    response = client.images.edit(**edit_params)
                    
                    # Save edited images
                    image_urls = []
                    for i, image_data in enumerate(response.data):
                        # Generate unique filename
                        output_filename = f"edited_{uuid.uuid4().hex}_{i}.png"
                        output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                        
                        # Download and save image
                        image_bytes = base64.b64decode(image_data.b64_json)
                        with open(output_filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        image_urls.append(f'/download/{output_filename}')
                    
                    resp = jsonify({
                        'success': True,
                        'images': image_urls,
                        'prompt': prompt,
                        'parameters': {
                            'size': size,
                            'quality': quality,
                            'count': n,
                            'had_mask': mask_filepath is not None,
                            'input_fidelity': input_fidelity
                        }
                    })
                    
                finally:
                    if mask_file_obj:
                        mask_file_obj.close()
        
        finally:
            # Clean up temporary files no matter what
            try:
                if temp_filepath and os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                if mask_filepath and os.path.exists(mask_filepath):
                    os.remove(mask_filepath)
            except OSError:
                pass
        
        return resp
            
    except APIError as e:
        print(f"OpenAI API Error in edit: {e}", file=sys.stderr)
        return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500
    except Exception as e:
        print(f"Server Error in edit: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Secure the filename to prevent directory traversal
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.route('/preview/<filename>')
def preview_file(filename):
    try:
        # Secure the filename to prevent directory traversal
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath)
    except Exception as e:
        return jsonify({'error': f'Preview error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Server will be available at: http://localhost:8080")
    try:
        app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()