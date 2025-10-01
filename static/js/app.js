// OCR CCCD Web App JavaScript

class OCRApp {
  constructor() {
    this.initializeEventListeners();
    this.initializeSliders();
  }

  initializeEventListeners() {
    // File input change
    document.getElementById("fileInput").addEventListener("change", (e) => {
      this.handleFileSelect(e);
    });

    // Form submission
    document.getElementById("uploadForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleFormSubmit(e);
    });

    // Range sliders
    document.getElementById("cropConf").addEventListener("input", (e) => {
      document.getElementById("cropConfValue").textContent = e.target.value;
    });

    document.getElementById("ocrConf").addEventListener("input", (e) => {
      document.getElementById("ocrConfValue").textContent = e.target.value;
    });
  }

  initializeSliders() {
    // Set initial values for sliders
    document.getElementById("cropConfValue").textContent =
      document.getElementById("cropConf").value;
    document.getElementById("ocrConfValue").textContent =
      document.getElementById("ocrConf").value;
  }

  handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
      this.showImagePreview(file);
      this.hideWelcomeMessage();
    }
  }

  showImagePreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const previewImg = document.getElementById("previewImg");
      previewImg.src = e.target.result;
      document.getElementById("imagePreview").style.display = "block";
    };
    reader.readAsDataURL(file);
  }

  hideWelcomeMessage() {
    document.getElementById("welcomeMessage").style.display = "none";
  }

  showWelcomeMessage() {
    document.getElementById("welcomeMessage").style.display = "block";
    document.getElementById("imagePreview").style.display = "none";
    document.getElementById("resultsContainer").style.display = "none";
  }

  async handleFormSubmit(event) {
    const formData = new FormData(event.target);
    const submitBtn = document.getElementById("submitBtn");
    const progressContainer = document.getElementById("progressContainer");
    const progressBar = progressContainer.querySelector(".progress-bar");
    const progressText = document.getElementById("progressText");

    // Show progress
    progressContainer.style.display = "block";
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';

    // Simulate progress
    this.simulateProgress(progressBar, progressText);

    try {
      const response = await fetch("/api/ocr", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        this.displayResults(result.data);
        this.showToast("Xử lý thành công!", "success");
      } else {
        throw new Error(result.error || "Có lỗi xảy ra");
      }
    } catch (error) {
      console.error("Error:", error);
      this.showToast("Lỗi: " + error.message, "error");
      this.showWelcomeMessage();
    } finally {
      // Hide progress
      progressContainer.style.display = "none";
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-magic"></i> Xử lý OCR';
    }
  }

  simulateProgress(progressBar, progressText) {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress > 90) progress = 90;

      progressBar.style.width = progress + "%";

      if (progress < 30) {
        progressText.textContent = "Đang tải ảnh...";
      } else if (progress < 60) {
        progressText.textContent = "Đang phát hiện góc...";
      } else if (progress < 90) {
        progressText.textContent = "Đang nhận dạng văn bản...";
      } else {
        progressText.textContent = "Hoàn thành!";
      }
    }, 200);

    // Clear interval after 3 seconds
    setTimeout(() => {
      clearInterval(interval);
    }, 3000);
  }

  displayResults(data) {
    this.displaySummaryCards(data);
    this.displayDetailedResults(data);

    document.getElementById("resultsContainer").style.display = "block";
  }

  displaySummaryCards(data) {
    const summaryCards = document.getElementById("summaryCards");
    const fields = data.fields || [];

    // Lọc bỏ các trường không hợp lệ
    const validFields = fields.filter(
      (field) =>
        field &&
        field.text &&
        field.text.trim() &&
        field.confidence !== undefined &&
        field.confidence >= 0
    );

    // Count fields with high confidence
    const highConfidenceFields = validFields.filter(
      (field) => field.confidence > 0.7
    ).length;
    const totalFields = validFields.length;
    const avgConfidence =
      totalFields > 0
        ? (
            (validFields.reduce((sum, field) => sum + field.confidence, 0) /
              totalFields) *
            100
          ).toFixed(1)
        : 0;

    summaryCards.innerHTML = `
            <div class="col-md-4">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                        <h6>Trường đã nhận dạng</h6>
                        <div class="value">${highConfidenceFields}/${totalFields}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <i class="fas fa-percentage fa-2x text-primary mb-2"></i>
                        <h6>Độ tin cậy trung bình</h6>
                        <div class="value">${avgConfidence}%</div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card summary-card">
                    <div class="card-body text-center">
                        <i class="fas fa-clock fa-2x text-warning mb-2"></i>
                        <h6>Thời gian xử lý</h6>
                        <div class="value">${data.runtime_ms || 0}ms</div>
                    </div>
                </div>
            </div>
        `;
  }

  displayDetailedResults(data) {
    const detailedResults = document.getElementById("detailedResults");
    const fields = data.fields || [];

    if (fields.length === 0) {
      detailedResults.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    Không tìm thấy thông tin nào trong ảnh. Vui lòng thử với ảnh khác hoặc điều chỉnh ngưỡng confidence xuống thấp hơn.
                </div>
            `;
      return;
    }

    // Lọc bỏ các trường có text rỗng hoặc không hợp lệ
    const validFields = fields.filter(
      (field) =>
        field &&
        field.text &&
        field.text.trim() &&
        field.confidence !== undefined &&
        field.confidence >= 0
    );

    if (validFields.length === 0) {
      detailedResults.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i>
                    Tất cả các trường được nhận diện đều không hợp lệ. Vui lòng thử lại với ngưỡng confidence khác.
                </div>
            `;
      return;
    }

    // Chia validFields thành 2 cột
    const midPoint = Math.ceil(validFields.length / 2);
    const leftColumn = validFields.slice(0, midPoint);
    const rightColumn = validFields.slice(midPoint);

    const createFieldHTML = (field) => {
      const confidenceClass =
        field.confidence > 0.7
          ? "success"
          : field.confidence > 0.5
          ? "warning"
          : "danger";

      // Làm sạch text hiển thị
      const cleanText = field.text ? field.text.trim() : "";
      const displayText = cleanText || "Không xác định";

      return `
                <div class="field-item">
                    <div class="field-label">
                        <i class="fas fa-tag"></i> ${this.formatFieldName(
                          field.name
                        )}
                        <span class="confidence-badge badge bg-${confidenceClass} float-end">
                            ${(field.confidence * 100).toFixed(1)}%
                        </span>
                    </div>
                    <div class="field-value">${displayText}</div>
                </div>
            `;
    };

    const leftColumnHTML = leftColumn.map(createFieldHTML).join("");
    const rightColumnHTML = rightColumn.map(createFieldHTML).join("");

    detailedResults.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    ${leftColumnHTML}
                </div>
                <div class="col-md-6">
                    ${rightColumnHTML}
                </div>
            </div>
        `;
  }

  formatFieldName(fieldName) {
    const fieldNames = {
      id: "Số căn cước",
      name: "Họ và tên",
      dob: "Ngày sinh",
      gender: "Giới tính",
      nationality: "Quốc tịch",
      origin_place: "Quê quán",
      current_place: "Nơi thường trú",
      expire_date: "Ngày hết hạn",
      issue_date: "Ngày cấp",
    };

    return fieldNames[fieldName] || fieldName;
  }

  showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    const toastBody = document.getElementById("toastBody");
    const toastHeader = toast.querySelector(".toast-header");

    // Set message
    toastBody.textContent = message;

    // Set icon and color based on type
    const icon = toastHeader.querySelector("i");
    icon.className =
      type === "success"
        ? "fas fa-check-circle text-success me-2"
        : type === "error"
        ? "fas fa-exclamation-circle text-danger me-2"
        : "fas fa-info-circle text-primary me-2";

    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
  }
}

// Initialize app when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  new OCRApp();
});

// Add some utility functions
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    // Show success message
    const toast = document.getElementById("toast");
    const toastBody = document.getElementById("toastBody");
    toastBody.textContent = "Đã sao chép vào clipboard!";
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
  });
}

// Add copy functionality to field values
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("field-value")) {
    copyToClipboard(e.target.textContent);
  }
});
