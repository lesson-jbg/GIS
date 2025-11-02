from flask import Flask, render_template, request, jsonify
import requests
import base64
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Replace with your n8n webhook URL
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/recevie-image"

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_workflow():
    try:
        if 'workflow_image' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['workflow_image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Read file content
        file_content = file.read()
        
        # Convert to base64 for API transmission
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Get user prompt if provided
        user_prompt = request.form.get('user_prompt', '').strip()
        
        # Send to n8n webhook
        payload = {
            'image': base64_image,
            'filename': secure_filename(file.filename),
            'content_type': file.content_type,
            'user_prompt': user_prompt if user_prompt else None
        }
        
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'sql_queries': result.get('sql_queries', []),
                'views': result.get('views', []),
                'analysis': result.get('analysis', ''),
                'user_prompt': user_prompt  # Return the prompt for confirmation
            })
        else:
            return jsonify({
                'error': 'Backend processing failed',
                'details': response.text
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout - analysis taking too long'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)