# OCR CCCD Card Reader

A complete pipeline for extracting text information from Vietnamese CCCD (Căn cước công dân) cards using YOLO object detection and VietOCR text recognition.

## Features

- **Two-stage Pipeline**: Corner detection + field extraction
- **YOLO Detection**: Detects CCCD corners and text fields with high accuracy
- **VietOCR Integration**: Vietnamese text recognition with confidence scores
- **Flexible Input**: Supports various image formats and orientations
- **JSON Output**: Structured data with confidence scores and runtime metrics

## Project Structure

```
ocr-cccd-card/
├── configs/                 # VietOCR configuration files
│   ├── base.yml
│   ├── vgg-transformer.yml
│   └── vocab/vi.yml
├── stages/                  # Core processing modules
│   ├── crop.py             # Corner detection and card cropping
│   └── ocr.py              # Field detection and text extraction
├── weights/                 # Model weights (excluded from git)
│   ├── models/
│   │   ├── best-corner-detect.pt
│   │   └── best-fields-detect.pt
│   └── vgg_transformer.pth
├── test-model/             # Test images and notebooks
│   ├── img/
│   └── *.ipynb
├── pipeline-ocr-cccd.py    # Complete pipeline script
└── test-*.sh              # Test scripts
```

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd ocr-cccd-card
   ```

2. **Create virtual environment**

   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Download model weights**
   - Place YOLO weights in `weights/models/`
   - Place VietOCR weights as `weights/vgg_transformer.pth`

## Usage

### Quick Start

**Full Pipeline (Recommended)**

```bash
bash test-pipeline.sh
```

**Individual Stages**

1. **Corner Detection & Cropping**

   ```bash
   python stages/crop.py \
     --image test-model/img/7739.jpg \
     --model weights/models/best-corner-detect.pt \
     --device cpu \
     --conf 0.3 \
     --deskew \
     --expand 0.06 \
     --aspect 1.585
   ```

2. **Field Detection & OCR**
   ```bash
   python stages/ocr.py \
     --image test-model/img/7739_cropped.jpg \
     --weights weights/models/best-fields-detect.pt \
     --device cpu \
     --ocr-conf 0.4 \
     --output output_ocr.json
   ```

### Pipeline Script

```bash
python pipeline-ocr-cccd.py \
  --image test-model/img/7739.jpg \
  --output output_pipeline.json \
  --crop-model weights/models/best-corner-detect.pt \
  --weights weights/models/best-fields-detect.pt \
  --device cpu
```

## Configuration

### YOLO Models

- **Corner Detection**: Detects 4 corners of CCCD card
- **Field Detection**: Detects text regions (ID, name, DOB, etc.)

### VietOCR Settings

- **Model**: VGG-Transformer architecture
- **Language**: Vietnamese vocabulary
- **Device**: CPU/GPU support

### Parameters

- `--conf`: YOLO confidence threshold (default: 0.25)
- `--ocr-conf`: OCR processing threshold (default: 0.4)
- `--device`: Computation device (cpu/cuda:0)
- `--crop-expand`: Expand detected corners (default: 0.06)
- `--crop-aspect`: Target aspect ratio (default: 1.585)

## Testing

**Test Scripts Available:**

- `test-pipeline.sh`: Full pipeline test
- `test-ocr.sh`: OCR-only test
- `test-crop-img.sh`: Corner detection test

**Jupyter Notebooks:**

- `test-model/test-detect.ipynb`: Field detection visualization
- `test-model/test-detect-corner.ipynb`: Corner detection visualization

## Troubleshooting

### Common Issues

1. **Pillow Compatibility Error**

   ```
   module 'PIL.Image' has no attribute 'ANTIALIAS'
   ```

   - Fixed automatically in the code with compatibility shim

2. **Model Weights Not Found**

   - Ensure weights are in correct paths
   - Check file permissions

3. **Empty OCR Results**

   - Lower `--ocr-conf` threshold
   - Check image quality and lighting
   - Verify VietOCR weights are loaded

4. **Path Issues**
   - Use absolute paths in scripts
   - Ensure working directory is project root

### Debug Mode

Add `--debug` flag to see detailed processing information:

```bash
python stages/ocr.py --debug --image your_image.jpg
```

## Dependencies

- **ultralytics**: YOLO object detection
- **vietocr**: Vietnamese text recognition
- **torch**: Deep learning framework
- **PIL/Pillow**: Image processing
- **numpy**: Numerical operations
- **opencv-python**: Computer vision utilities

## Performance

- **Typical Runtime**: 2-4 seconds per image (CPU)
- **Accuracy**: >90% for clear, well-lit CCCD images
- **Supported Formats**: JPG, PNG, BMP, TIFF

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

[Add your license information here]

## Acknowledgments

- YOLO models trained on CCCD dataset
- VietOCR for Vietnamese text recognition
- Ultralytics for YOLO implementation
