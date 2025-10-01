import os
import json
import tempfile
import sys
import importlib.util
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

def _load_pipeline_function():
    """Load the run_pipeline function from pipeline-ocr-cccd.py"""
    pipeline_path = Path(__file__).parent / "pipeline-ocr-cccd.py"
    spec = importlib.util.spec_from_file_location("pipeline_ocr_cccd", str(pipeline_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {pipeline_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_ocr_cccd"] = module
    spec.loader.exec_module(module)
    return module.run_pipeline

# Load the pipeline function
run_pipeline = _load_pipeline_function()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Tạo thư mục upload và output nếu chưa có
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Cấu hình cho phép upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ocr', methods=['POST'])
def ocr_api():
    try:
        # Kiểm tra file upload
        if 'file' not in request.files:
            return jsonify({'error': 'Không có file được upload'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Không có file được chọn'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Định dạng file không được hỗ trợ'}), 400
        
        # Lưu file upload
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(input_path)
        
        # Tạo tên file output
        output_filename = f"{uuid.uuid4()}_result.json"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Sử dụng tham số mặc định
        crop_conf = 0.7
        ocr_conf = 0.7
        device = 'cpu'
        
        # Chạy pipeline OCR
        result = run_pipeline(
            image=Path(input_path),
            output_json=Path(output_path),
            crop_model=Path("weights/models/best-corner-detect.pt"),
            crop_device=device if device != 'cpu' else None,
            crop_conf=crop_conf,
            crop_deskew=True,
            crop_expand=0.1,
            crop_aspect=1.585,
            ocr_weights=Path("weights/models/best-fields-detect.pt"),
            ocr_device=device,
            ocr_conf=ocr_conf,
            ocr_iou=0.5,
        )
        
        # Thêm thông tin file vào kết quả
        result['input_filename'] = filename
        result['processed_at'] = str(Path(input_path).stat().st_mtime)


        # Chuyển đổi dữ liệu thành format mà frontend mong đợi
        fields = []
        if 'data' in result and 'yolo_confidence' in result:
            for field_name, field_value in result['data'].items():
                if field_value and field_value.strip():  # Chỉ thêm field có giá trị
                    confidence = result.get('yolo_confidence', {}).get(field_name, 0.0)
                    fields.append({
                        'name': field_name,
                        'text': field_value,
                        'confidence': confidence
                    })
        
        # Tạo response data mới
        response_data = {
            'fields': fields,
            'runtime_ms': result.get('runtime_ms', 0),
            'cropped_image': result.get('cropped_image', ''),
            'input_filename': filename,
            'processed_at': str(Path(input_path).stat().st_mtime)
        }
        
        # Xóa file tạm thời
        try:
            os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        # Xóa file tạm thời nếu có lỗi
        try:
            if 'input_path' in locals():
                os.remove(input_path)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'OCR CCCD API is running'
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File quá lớn. Kích thước tối đa là 16MB'}), 413

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
