import os
import json
import tempfile
import sys
import importlib.util
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pandas as pd
import io

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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ocr_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class OCRRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    crop_conf = db.Column(db.Float, nullable=False)
    ocr_conf = db.Column(db.Float, nullable=False)
    device = db.Column(db.String(50), nullable=False)
    runtime_ms = db.Column(db.Integer, nullable=False)
    fields_data = db.Column(db.Text, nullable=False)  # JSON string
    confidence_data = db.Column(db.Text, nullable=False)  # JSON string
    image_path = db.Column(db.String(500), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'created_at': self.created_at.isoformat(),
            'crop_conf': self.crop_conf,
            'ocr_conf': self.ocr_conf,
            'device': self.device,
            'runtime_ms': self.runtime_ms,
            'fields_data': json.loads(self.fields_data),
            'confidence_data': json.loads(self.confidence_data),
            'image_path': self.image_path
        }

# Tạo thư mục upload và output nếu chưa có
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize database
with app.app_context():
    db.create_all()

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
        
        # Lấy tham số từ form với giá trị mặc định cao hơn để tăng độ chính xác
        crop_conf = float(request.form.get('crop_conf', 0.5))
        ocr_conf = float(request.form.get('ocr_conf', 0.4))
        device = request.form.get('device', 'cpu')
        
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
                # Kiểm tra field_value có hợp lệ không
                if field_value and isinstance(field_value, str) and field_value.strip():
                    # Làm sạch text (loại bỏ ký tự lạ, chỉ giữ lại ký tự hợp lệ)
                    cleaned_value = field_value.strip()
                    # Kiểm tra confidence có hợp lệ không
                    confidence = result.get('yolo_confidence', {}).get(field_name, 0.0)
                    if isinstance(confidence, (int, float)) and confidence >= 0:
                        fields.append({
                            'name': field_name,
                            'text': cleaned_value,
                            'confidence': round(float(confidence), 1)
                        })
        
        # Tạo response data mới
        response_data = {
            'fields': fields,
            'runtime_ms': result.get('runtime_ms', 0),
            'cropped_image': result.get('cropped_image', ''),
            'input_filename': filename,
            'processed_at': str(Path(input_path).stat().st_mtime)
        }
        
        # Lưu vào database
        try:
            # Tạo record mới
            record = OCRRecord(
                filename=filename,
                original_filename=file.filename,
                crop_conf=crop_conf,
                ocr_conf=ocr_conf,
                device=device,
                runtime_ms=result.get('runtime_ms', 0),
                fields_data=json.dumps(result.get('data', {})),
                confidence_data=json.dumps(result.get('yolo_confidence', {})),
                image_path=input_path
            )
            db.session.add(record)
            db.session.commit()
            
            # Thêm ID vào response
            response_data['record_id'] = record.id
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            # Không dừng xử lý nếu lưu DB lỗi
        
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

# API routes for history management
@app.route('/api/history')
def get_history():
    """Lấy danh sách lịch sử OCR"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        records = OCRRecord.query.order_by(OCRRecord.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'records': [record.to_dict() for record in records.items],
                'total': records.total,
                'pages': records.pages,
                'current_page': page
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/<int:record_id>')
def get_history_record(record_id):
    """Lấy chi tiết một record OCR"""
    try:
        record = OCRRecord.query.get_or_404(record_id)
        return jsonify({
            'success': True,
            'data': record.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/<format>')
def export_data(format):
    """Xuất dữ liệu theo format (csv, excel, json)"""
    try:
        # Lấy tất cả records
        records = OCRRecord.query.order_by(OCRRecord.created_at.desc()).all()
        
        if not records:
            return jsonify({'success': False, 'error': 'Không có dữ liệu để xuất'}), 404
        
        # Chuẩn bị dữ liệu
        data = []
        for record in records:
            fields_data = json.loads(record.fields_data)
            confidence_data = json.loads(record.confidence_data)
            
            row = {
                'ID': record.id,
                'Tên file gốc': record.original_filename,
                'Ngày tạo': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Ngưỡng phát hiện góc': record.crop_conf,
                'Ngưỡng OCR': record.ocr_conf,
                'Thiết bị': record.device,
                'Thời gian xử lý (ms)': record.runtime_ms
            }
            
            # Thêm các trường OCR
            for field_name, field_value in fields_data.items():
                confidence = confidence_data.get(field_name, 0)
                row[f'{field_name} (text)'] = field_value
                row[f'{field_name} (confidence)'] = confidence
            
            data.append(row)
        
        # Tạo DataFrame
        df = pd.DataFrame(data)
        
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'ocr_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
        
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='OCR History')
            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'ocr_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            )
        
        elif format.lower() == 'json':
            return send_file(
                io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'ocr_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
        
        else:
            return jsonify({'success': False, 'error': 'Format không hỗ trợ'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Xóa một record OCR"""
    try:
        record = OCRRecord.query.get_or_404(record_id)
        db.session.delete(record)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã xóa record thành công'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Removed bbox route - no longer needed

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File quá lớn. Kích thước tối đa là 16MB'}), 413

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
