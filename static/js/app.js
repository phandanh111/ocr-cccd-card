// OCR CCCD Web App JavaScript

class OCRApp {
  constructor() {
    this.initializeEventListeners();
    this.initializeSliders();
    this.loadHistory();
    this.currentRecordId = null;
    this.bboxData = {};
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
    const files = event.target.files;
    if (files && files.length > 0) {
      this.showImagePreview(files[0]);
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

  showResultImagePreview() {
    // Show the uploaded image in preview
    const fileInput = document.getElementById("fileInput");
    if (fileInput.files && fileInput.files[0]) {
      this.showImagePreview(fileInput.files[0]);
    }
  }

  // (removed multi-image preview)

  hideWelcomeMessage() {
    document.getElementById("welcomeMessage").style.display = "none";
  }

  showWelcomeMessage() {
    document.getElementById("welcomeMessage").style.display = "block";
    document.getElementById("imagePreview").style.display = "none";
    document.getElementById("resultsContainer").style.display = "none";
  }

  async handleFormSubmit(event) {
    const files = document.getElementById("fileInput").files;
    const submitBtn = document.getElementById("submitBtn");
    const progressContainer = document.getElementById("progressContainer");
    const progressBar = progressContainer.querySelector(".progress-bar");
    const progressText = document.getElementById("progressText");

    if (files.length === 0) {
      this.showToast("Vui lòng chọn ít nhất một ảnh", "error");
      return;
    }

    // Show progress
    progressContainer.style.display = "block";
    submitBtn.disabled = true;

    try {
      // Single file processing only
      submitBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';
      this.simulateProgress(progressBar, progressText);

      const formData = new FormData();

      // Add file
      const fileInput = document.getElementById("fileInput");
      if (fileInput.files && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      // Add config
      formData.append("crop_conf", document.getElementById("cropConf").value);
      formData.append("ocr_conf", document.getElementById("ocrConf").value);
      formData.append("device", document.getElementById("device").value);

      const response = await fetch("/api/ocr", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        this.displayResults(result.data);
        this.showToast("Xử lý thành công!", "success");
        this.loadHistory();
      } else {
        throw new Error(result.error || "Có lỗi xảy ra");
      }
    } catch (error) {
      console.error("Error:", error);
      this.showToast("Lỗi: " + error.message, "error");
      // Don't show welcome message - keep the uploaded image visible
      // this.showWelcomeMessage();
    } finally {
      // Hide progress
      progressContainer.style.display = "none";
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-magic"></i> Xử lý OCR';

      // Don't reset the form - keep the file selected
      // document.getElementById("uploadForm").reset();
    }
  }

  // (removed multi-file processing)

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

    // Show image preview if available
    if (data.input_filename) {
      this.showResultImagePreview();
    }

    // Hide welcome message and show results
    this.hideWelcomeMessage();
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
                        <div class="field-actions">
                            <span class="confidence-badge badge bg-${confidenceClass}">
                                ${(field.confidence * 100).toFixed(1)}%
                            </span>
                            <button class="btn btn-outline-primary btn-sm ms-2" onclick="event.stopPropagation(); app.editField('${
                              field.name
                            }', '${displayText.replace(/'/g, "\\'")}')">
                                <i class="fas fa-edit"></i>
                            </button>
                        </div>
                    </div>
                    <div class="field-value" id="field-value-${
                      field.name
                    }">${displayText}</div>
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

  // History Management Functions
  async loadHistory() {
    try {
      const response = await fetch("/api/history?per_page=20");
      const result = await response.json();

      if (result.success) {
        this.displayHistory(result.data.records);
      }
    } catch (error) {
      console.error("Error loading history:", error);
    }
  }

  displayHistory(records) {
    const historyList = document.getElementById("historyList");

    if (!records || records.length === 0) {
      historyList.innerHTML = `
        <div class="text-center text-muted">
          <i class="fas fa-inbox"></i>
          <p class="mt-2">Chưa có lịch sử quét nào</p>
        </div>
      `;
      return;
    }

    const historyHTML = records
      .map((record) => {
        const createdDate = new Date(record.created_at).toLocaleString("vi-VN");
        const fieldsCount = Object.keys(record.fields_data).length;

        return `
        <div class="history-item" onclick="app.loadHistoryRecord(${record.id})">
          <div class="history-title">${record.original_filename}</div>
          <div class="history-meta">
            <span>${createdDate}</span>
            <span>${fieldsCount} trường</span>
          </div>
          <div class="history-actions mt-2">
            <button class="btn btn-outline-primary btn-sm" onclick="event.stopPropagation(); app.loadHistoryRecord(${record.id})">
              <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-outline-danger btn-sm" onclick="event.stopPropagation(); app.deleteRecord(${record.id})">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      `;
      })
      .join("");

    historyList.innerHTML = historyHTML;
  }

  async loadHistoryRecord(recordId) {
    try {
      const response = await fetch(`/api/history/${recordId}`);
      const result = await response.json();

      if (result.success) {
        const record = result.data;

        // Convert to display format
        const fields = [];
        const fieldsData = record.fields_data;
        const confidenceData = record.confidence_data;

        for (const [fieldName, fieldValue] of Object.entries(fieldsData)) {
          if (fieldValue && fieldValue.trim()) {
            const confidence = confidenceData[fieldName] || 0;
            fields.push({
              name: fieldName,
              text: fieldValue,
              confidence: confidence,
            });
          }
        }

        const displayData = {
          fields: fields,
          runtime_ms: record.runtime_ms,
          input_filename: record.original_filename,
          processed_at: record.created_at,
          record_id: record.id,
        };

        // Switch to OCR tab and display results
        document.getElementById("ocr-tab").click();
        this.displayResults(displayData);
        this.showToast("Đã tải lại kết quả từ lịch sử", "success");
      }
    } catch (error) {
      console.error("Error loading history record:", error);
      this.showToast("Lỗi khi tải lịch sử", "error");
    }
  }

  async deleteRecord(recordId) {
    if (!confirm("Bạn có chắc muốn xóa record này?")) {
      return;
    }

    try {
      const response = await fetch(`/api/delete/${recordId}`, {
        method: "DELETE",
      });
      const result = await response.json();

      if (result.success) {
        this.showToast("Đã xóa record thành công", "success");
        this.loadHistory(); // Reload history
      } else {
        this.showToast("Lỗi khi xóa record", "error");
      }
    } catch (error) {
      console.error("Error deleting record:", error);
      this.showToast("Lỗi khi xóa record", "error");
    }
  }

  // Image and Highlight Functions removed

  // Manual Edit Functions
  editField(fieldName, currentValue) {
    const newValue = prompt(
      `Chỉnh sửa ${this.formatFieldName(fieldName)}:`,
      currentValue
    );

    if (newValue !== null && newValue !== currentValue) {
      // Update the display
      const fieldValueElement = document.getElementById(
        `field-value-${fieldName}`
      );
      if (fieldValueElement) {
        fieldValueElement.textContent = newValue;
        fieldValueElement.style.color = "#28a745"; // Green to indicate edited
        fieldValueElement.style.fontWeight = "bold";
      }

      // Store the edited value
      if (!this.editedFields) {
        this.editedFields = {};
      }
      this.editedFields[fieldName] = newValue;

      // Show save button
      this.showSaveButton();

      this.showToast(
        `Đã cập nhật ${this.formatFieldName(fieldName)}`,
        "success"
      );
    }
  }

  getEditedData() {
    return this.editedFields || {};
  }

  hasEdits() {
    return this.editedFields && Object.keys(this.editedFields).length > 0;
  }

  showSaveButton() {
    const saveContainer = document.getElementById("saveEditsContainer");
    if (saveContainer) {
      saveContainer.style.display = "block";
    }
  }

  hideSaveButton() {
    const saveContainer = document.getElementById("saveEditsContainer");
    if (saveContainer) {
      saveContainer.style.display = "none";
    }
  }

  saveEdits() {
    if (!this.hasEdits()) {
      this.showToast("Không có thay đổi nào để lưu", "warning");
      return;
    }

    // In a real implementation, you would send the edited data to the server
    // For now, we'll just show a success message
    this.showToast("Đã lưu các chỉnh sửa thành công!", "success");

    // Clear edited fields and hide save button
    this.editedFields = {};
    this.hideSaveButton();

    // Reset field colors
    document.querySelectorAll(".field-value").forEach((element) => {
      element.style.color = "#495057";
      element.style.fontWeight = "500";
    });
  }

  discardEdits() {
    if (!this.hasEdits()) {
      this.showToast("Không có thay đổi nào để hủy", "warning");
      return;
    }

    if (confirm("Bạn có chắc muốn hủy tất cả các thay đổi?")) {
      // Reset all edited fields to original values
      for (const [fieldName, originalValue] of Object.entries(
        this.editedFields
      )) {
        const fieldValueElement = document.getElementById(
          `field-value-${fieldName}`
        );
        if (fieldValueElement) {
          // Get original value from the current data
          const currentFields = this.getCurrentFields();
          const originalField = currentFields.find((f) => f.name === fieldName);
          if (originalField) {
            fieldValueElement.textContent = originalField.text;
          }
          fieldValueElement.style.color = "#495057";
          fieldValueElement.style.fontWeight = "500";
        }
      }

      this.editedFields = {};
      this.hideSaveButton();
      this.showToast("Đã hủy tất cả các thay đổi", "info");
    }
  }

  getCurrentFields() {
    // This would need to be implemented to get current field data
    // For now, return empty array
    return [];
  }

  // Bulk Processing Functions
  displayBulkResults(results) {
    const successCount = results.filter((r) => r.success).length;
    const failCount = results.length - successCount;

    let resultsHTML = `
      <div class="alert alert-info">
        <h5><i class="fas fa-tasks"></i> Kết quả xử lý hàng loạt</h5>
        <p>Tổng: ${results.length} ảnh | Thành công: ${successCount} | Lỗi: ${failCount}</p>
      </div>
    `;

    results.forEach((result, index) => {
      const statusClass = result.success ? "success" : "danger";
      const statusIcon = result.success ? "check-circle" : "times-circle";

      resultsHTML += `
        <div class="card mb-2">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <h6 class="mb-1">${result.filename}</h6>
                ${
                  result.success
                    ? `<small class="text-muted">${result.data.fields.length} trường được nhận diện</small>`
                    : `<small class="text-danger">${result.error}</small>`
                }
              </div>
              <span class="badge bg-${statusClass}">
                <i class="fas fa-${statusIcon}"></i>
                ${result.success ? "Thành công" : "Lỗi"}
              </span>
            </div>
          </div>
        </div>
      `;
    });

    // Show results in a modal or dedicated area
    this.showBulkResultsModal(resultsHTML);
  }

  showBulkResultsModal(content) {
    // Create modal if it doesn't exist
    let modal = document.getElementById("bulkResultsModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "bulkResultsModal";
      modal.className = "modal fade";
      modal.innerHTML = `
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Kết quả xử lý hàng loạt</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="bulkResultsContent">
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    document.getElementById("bulkResultsContent").innerHTML = content;

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
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
  window.app = new OCRApp();
});

// Global functions for export
async function exportData(format) {
  try {
    const response = await fetch(`/api/export/${format}`);

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Map format to correct file extension
      const fileExtensions = {
        csv: "csv",
        excel: "xlsx",
        json: "json",
      };
      const extension = fileExtensions[format] || format;

      a.download = `ocr_history_${new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/:/g, "-")}.${extension}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      app.showToast(
        `Đã xuất dữ liệu ${format.toUpperCase()} thành công`,
        "success"
      );
    } else {
      const result = await response.json();
      app.showToast(result.error || "Lỗi khi xuất dữ liệu", "error");
    }
  } catch (error) {
    console.error("Error exporting data:", error);
    app.showToast("Lỗi khi xuất dữ liệu", "error");
  }
}

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
