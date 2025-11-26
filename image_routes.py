from flask import Blueprint, request, jsonify, current_app, send_from_directory
import os
from werkzeug.utils import secure_filename
from functools import wraps
try:
    # Intentar import relativo primero (funciona cuando se ejecuta como paquete)
    from .file_utils import save_uploaded_file, get_upload_path
except ImportError:
    try:
        # Intentar import absoluto (funciona cuando belgrano_tickets está en path)
        from belgrano_tickets.file_utils import save_uploaded_file, get_upload_path
    except ImportError:
        # Fallback: agregar directorio actual al path e importar directo
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from file_utils import save_uploaded_file, get_upload_path
import sqlite3

# Create blueprint for image routes
image_bp = Blueprint('images', __name__)

def get_db_connection():
    """Get a database connection"""
    from belgrano_tickets import get_db
    return get_db()

def update_entity_image(entity_type, entity_id, image_url):
    """Update the image_url for the specified entity"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if entity_type == 'business':
            cursor.execute(
                'UPDATE negocios SET imagen = ? WHERE id = ?',
                (image_url, entity_id)
            )
        elif entity_type == 'branch':
            cursor.execute(
                'UPDATE sucursales SET imagen = ? WHERE id = ?',
                (image_url, entity_id)
            )
        elif entity_type == 'product':
            cursor.execute(
                'UPDATE productos SET imagen = ? WHERE id = ?',
                (image_url, entity_id)
            )
        else:
            return False
            
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        current_app.logger.error(f"Error updating {entity_type} image: {str(e)}")
        return False
    finally:
        conn.close()

@image_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """Handle file upload for business, branch, or product images"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    entity_type = request.form.get('entity_type')
    entity_id = request.form.get('entity_id')
    
    # Validate required fields
    if not entity_type or entity_type not in ['business', 'branch', 'product']:
        return jsonify({'error': 'Invalid or missing entity_type'}), 400
        
    if not entity_id or not entity_id.isdigit():
        return jsonify({'error': 'Invalid or missing entity_id'}), 400
    
    entity_id = int(entity_id)
    
    # If user does not select file, browser also submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        # Save the uploaded file
        filename = save_uploaded_file(file, entity_type)
        if not filename:
            return jsonify({'error': 'Invalid file type'}), 400
            
        # Get the public URL for the file
        image_url = get_upload_path(filename, entity_type)
        
        # Update the entity with the new image URL
        if update_entity_image(entity_type, entity_id, image_url):
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        else:
            # Clean up the uploaded file if database update failed
            try:
                file_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], 
                    entity_type, 
                    filename
                )
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"Error cleaning up file: {str(e)}")
                
            return jsonify({'error': 'Failed to update entity with image'}), 500
    
    return jsonify({'error': 'File upload failed'}), 400

# Add this route to serve media files
@image_bp.route('/media/<path:entity_type>/<path:filename>')
def serve_media(entity_type, filename):
    """Serve uploaded media files"""
    if entity_type not in ['business', 'branch', 'product']:
        return jsonify({'error': 'Invalid entity type'}), 404
        
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], entity_type)
    return send_from_directory(upload_dir, filename)
