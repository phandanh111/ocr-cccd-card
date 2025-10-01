# OCR Căn Cước Công Dân - Web Application

Ứng dụng web để trích xuất thông tin từ ảnh căn cước công dân Việt Nam sử dụng AI.

## 🌟 Tính năng

- **Giao diện web thân thiện**: Upload ảnh và xem kết quả ngay lập tức
- **AI-Powered**: Sử dụng YOLO và VietOCR để nhận dạng chính xác
- **Xử lý nhanh**: Kết quả trong vài giây
- **Cài đặt linh hoạt**: Điều chỉnh tham số để tối ưu kết quả
- **Bảo mật**: Không lưu trữ dữ liệu người dùng
- **Responsive**: Hoạt động tốt trên mọi thiết bị

## 🚀 Cài đặt và Chạy

### 1. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

### 2. Kiểm tra Model Weights

Đảm bảo các file model đã có trong thư mục:

- `weights/models/best-corner-detect.pt`
- `weights/models/best-fields-detect.pt`
- `weights/vgg_transformer.pth`

### 3. Chạy Web Application

```bash
python run_web.py
```

Hoặc chạy trực tiếp:

```bash
python app.py
```

### 4. Truy cập Web App

Mở trình duyệt và truy cập: http://localhost:8080

## 📱 Cách sử dụng

1. **Upload ảnh**: Chọn ảnh căn cước công dân (JPG, PNG, GIF, BMP, TIFF)
2. **Cài đặt nâng cao** (tùy chọn):
   - Điều chỉnh ngưỡng phát hiện góc
   - Điều chỉnh ngưỡng OCR
   - Chọn thiết bị xử lý (CPU/GPU)
3. **Xử lý**: Nhấn "Xử lý OCR" và chờ kết quả
4. **Xem kết quả**: Thông tin được trích xuất sẽ hiển thị với độ tin cậy

## 🛠️ Cấu trúc Project

```
ocr-cccd-card/
├── app.py                 # Flask web application
├── run_web.py            # Script khởi động web app
├── pipeline-ocr-cccd.py  # Core OCR pipeline
├── templates/
│   └── index.html        # Giao diện web chính
├── static/
│   ├── css/
│   │   └── style.css     # CSS styling
│   └── js/
│       └── app.js        # JavaScript functionality
├── uploads/              # Thư mục tạm cho file upload
├── outputs/              # Thư mục tạm cho kết quả
└── requirements.txt      # Python dependencies
```

## 🔧 API Endpoints

### POST /api/ocr

Xử lý OCR cho ảnh căn cước

**Parameters:**

- `file`: File ảnh (multipart/form-data)
- `crop_conf`: Ngưỡng phát hiện góc (0.1-1.0, default: 0.3)
- `ocr_conf`: Ngưỡng OCR (0.1-1.0, default: 0.25)
- `device`: Thiết bị xử lý (cpu/cuda:0, default: cpu)

**Response:**

```json
{
  "success": true,
  "data": {
    "fields": [
      {
        "name": "id",
        "text": "001234567890",
        "confidence": 0.95
      }
    ],
    "runtime_ms": 2500,
    "cropped_image": "path/to/cropped.jpg"
  }
}
```

### GET /api/health

Kiểm tra trạng thái API

**Response:**

```json
{
  "status": "healthy",
  "message": "OCR CCCD API is running"
}
```

## ⚙️ Cấu hình

### Tham số OCR

- **crop_conf**: Ngưỡng tin cậy cho việc phát hiện góc căn cước

  - Giá trị thấp (0.1-0.3): Phát hiện nhiều góc hơn, có thể có false positive
  - Giá trị cao (0.7-1.0): Chỉ phát hiện góc rõ ràng, có thể bỏ sót

- **ocr_conf**: Ngưỡng tin cậy cho việc nhận dạng văn bản
  - Giá trị thấp (0.1-0.3): Nhận dạng nhiều text hơn, có thể có lỗi
  - Giá trị cao (0.7-1.0): Chỉ hiển thị text có độ tin cậy cao

### Thiết bị xử lý

- **CPU**: Chậm hơn nhưng không cần GPU
- **GPU (CUDA)**: Nhanh hơn nhiều nếu có NVIDIA GPU

## 🐛 Troubleshooting

### Lỗi thường gặp

1. **"Model weights not found"**

   - Kiểm tra file model có trong thư mục `weights/`
   - Đảm bảo quyền đọc file

2. **"File too large"**

   - Giảm kích thước ảnh (tối đa 16MB)
   - Sử dụng ảnh JPG thay vì PNG

3. **"No fields detected"**

   - Thử giảm `crop_conf` và `ocr_conf`
   - Kiểm tra chất lượng ảnh (độ sáng, độ rõ nét)
   - Đảm bảo ảnh chứa căn cước công dân Việt Nam

4. **"Server error"**
   - Kiểm tra log trong terminal
   - Đảm bảo đã cài đặt đầy đủ dependencies

### Debug Mode

Chạy với debug mode để xem thông tin chi tiết:

```bash
FLASK_DEBUG=1 python app.py
```

## 📊 Performance

- **Thời gian xử lý**: 2-5 giây (CPU), 1-2 giây (GPU)
- **Độ chính xác**: >90% với ảnh chất lượng tốt
- **Định dạng hỗ trợ**: JPG, PNG, GIF, BMP, TIFF
- **Kích thước tối đa**: 16MB

## 🔒 Bảo mật

- File upload được xử lý tạm thời và tự động xóa
- Không lưu trữ dữ liệu người dùng
- API có giới hạn kích thước file
- Validation đầu vào nghiêm ngặt

## 🚀 Deployment

### Sử dụng Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker (Tùy chọn)

Tạo `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 📝 License

[Thêm thông tin license của bạn]

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📞 Support

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub hoặc liên hệ qua email.
