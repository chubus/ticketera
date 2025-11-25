import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, send_from_directory
from functools import wraps
import imghdr

def validate_image(stream):
    """Validate that the uploaded file is an image"""
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + format

def save_uploaded_file(file, entity_type):
    """Save uploaded file and return the filename"""
    if not file:
        return None
        
    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
        return None
        
    # Generate a secure filename with UUID
    filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create directory if it doesn't exist
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], entity_type)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    return filename

def get_upload_path(filename, entity_type):
    """Get the relative URL path for the uploaded file"""
    if not filename:
        return None
    return f"/media/{entity_type}/{filename}"

def serve_media_file(filename, entity_type):
    """Serve media files from the upload directory"""
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], entity_type)
    return send_from_directory(upload_dir, filename)
