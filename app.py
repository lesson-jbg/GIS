from flask import Flask, render_template, request, jsonify
import requests
import io
from PIL import Image
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
        
        # Get user prompt if provided
        user_prompt = request.form.get('user_prompt', '').strip()
        
        # Open image using PIL
        image = Image.open(file.stream)
        
        # Convert image to bytes (binary format)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format or 'PNG')
        img_byte_arr.seek(0)
        
        # Prepare the multipart form data
        files = {
            'image': (secure_filename(file.filename), img_byte_arr, file.content_type)
        }
        
        # Prepare form data with user prompt
        data = {
            'user_prompt': user_prompt if user_prompt else None,
            'filename': secure_filename(file.filename)
        }
        
        # Send to n8n webhook as multipart/form-data with binary image
        response = requests.post(
            N8N_WEBHOOK_URL, 
            files=files, 
            data=data, 
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Parse the response structure from n8n
            sql_queries = []
            views = []
            analysis = ""
            
            # Handle array response format
            if isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                
                # Extract steps array
                if 'steps' in first_item and isinstance(first_item['steps'], list):
                    for step in first_item['steps']:
                        # Extract SQL from description field
                        if 'description' in step:
                            description = step['description']
                            # Remove markdown code blocks if present
                            if description.startswith('```sql'):
                                description = description.replace('```sql', '').replace('```', '').strip()
                            sql_queries.append(description)
                        
                        # Also check sql field
                        if 'sql' in step:
                            sql_content = step['sql']
                            if sql_content and sql_content not in sql_queries:
                                sql_queries.append(sql_content)
                
                # Generate analysis summary
                if sql_queries:
                    analysis = f"Successfully generated {len(sql_queries)} SQL script(s) for your GIS workflow. The queries include table creation, spatial joins, and location analysis based on your specified criteria."
            
            # If no SQL queries found, check for direct fields (fallback)
            if not sql_queries:
                sql_queries = result.get('sql_queries', [])
                views = result.get('views', [])
                analysis = result.get('analysis', '')
            
            return jsonify({
                'success': True,
                'sql_queries': sql_queries,
                'views': views,
                'analysis': analysis if analysis else 'Analysis completed successfully.',
                'user_prompt': user_prompt
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