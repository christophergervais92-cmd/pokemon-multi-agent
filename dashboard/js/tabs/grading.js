// =============================================================================
// AI CARD GRADING TAB
// =============================================================================
//
// Provides AI-powered card grading analysis via image upload, drag-and-drop,
// clipboard paste, or URL input. Sends images to the backend /grader/analyze
// endpoint and renders predicted grades, subgrades, defects, and values.
//
// Globals referenced (defined elsewhere, available on window scope):
//   - api(path, options)  -- fetch wrapper for backend calls
// =============================================================================

let selectedImageData = null;

// ---------------------------------------------------------------------------
// Initialization -- wire up drag-and-drop, file input, and clipboard paste
// ---------------------------------------------------------------------------

function initGradingTab() {
    const dropZone = document.getElementById('dropZone');

    // Prevent default browser behaviour for all drag events on the drop zone
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
        dropZone?.addEventListener(event, e => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    // Visual feedback -- highlight on drag enter/over
    ['dragenter', 'dragover'].forEach(event => {
        dropZone?.addEventListener(event, () => dropZone.classList.add('drop-active'));
    });

    // Remove highlight on drag leave / drop
    ['dragleave', 'drop'].forEach(event => {
        dropZone?.addEventListener(event, () => dropZone.classList.remove('drop-active'));
    });

    // Handle dropped files
    dropZone?.addEventListener('drop', e => {
        const files = e.dataTransfer?.files;
        if (files?.length) handleImageFile(files[0]);
    });

    // File input change listener
    document.getElementById('gradeImageFile')?.addEventListener('change', e => {
        if (e.target.files?.length) handleImageFile(e.target.files[0]);
    });

    // Paste from clipboard (works globally so users can Ctrl+V anywhere)
    document.addEventListener('paste', e => {
        const items = e.clipboardData?.items;
        for (let item of items || []) {
            if (item.type.startsWith('image/')) {
                handleImageFile(item.getAsFile());
                break;
            }
        }
    });
}

// Run setup once the DOM is ready
document.addEventListener('DOMContentLoaded', initGradingTab);

// ---------------------------------------------------------------------------
// Image handling helpers
// ---------------------------------------------------------------------------

/**
 * Read an image File into a base64 data-URL and store it in selectedImageData.
 */
function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = e => {
        selectedImageData = e.target.result;
        showImagePreview(selectedImageData);
    };
    reader.readAsDataURL(file);
}

/**
 * Handle file selection from the <input type="file"> element (called via
 * onchange="handleGradeFileSelect(this)").
 */
function handleGradeFileSelect(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }
        const reader = new FileReader();
        reader.onload = e => {
            selectedImageData = e.target.result;
            showImagePreview(selectedImageData);
        };
        reader.readAsDataURL(file);
    }
}

/**
 * Display the selected/dropped/pasted image in the preview area.
 */
function showImagePreview(src) {
    const preview = document.getElementById('imagePreview');
    const img = document.getElementById('previewImg');
    img.src = src;
    preview.style.display = 'block';
}

// ---------------------------------------------------------------------------
// Grading analysis
// ---------------------------------------------------------------------------

/**
 * Send the selected image (base64 or URL) to the backend for AI grading
 * analysis, then render the results.
 */
async function gradeCard() {
    const urlInput = document.getElementById('gradeImageUrl').value;
    const imageData = selectedImageData || urlInput;

    if (!imageData) {
        alert('Please provide an image URL or upload a file');
        return;
    }

    const results = document.getElementById('gradeResults');
    const btn = document.getElementById('gradeBtn');

    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    results.innerHTML = '<div class="loading"><div class="spinner"></div>AI is analyzing your card...</div>';

    try {
        const payload = imageData.startsWith('data:')
            ? { image_base64: imageData }
            : { image_url: imageData };

        // Attach OpenAI key from local storage if the user configured one
        const openaiKey = localStorage.getItem('openai_api_key');
        if (openaiKey) {
            payload.openai_api_key = openaiKey;
        }

        const data = await api('/grader/analyze', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (data.error && !data.demo_mode) {
            results.innerHTML = `<div class="empty"><div class="empty-icon"></div>${data.error}</div>`;
            return;
        }

        renderGradeResults(data, imageData);

    } catch (e) {
        results.innerHTML = `<div class="empty"><div class="empty-icon"></div>${e.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Card';
    }
}

// ---------------------------------------------------------------------------
// Results rendering
// ---------------------------------------------------------------------------

/**
 * Render the AI grading analysis results into the #gradeResults container.
 */
function renderGradeResults(data, imageUrl) {
    const results = document.getElementById('gradeResults');

    const grades = data.predicted_grades || {};
    const subgrades = data.subgrades || {};
    const psaGrade = grades.PSA || data.estimated_psa_grade || 8;

    // Determine grade badge class based on PSA grade
    let badgeClass = 'mid';
    if (psaGrade >= 10) badgeClass = 'gem';
    else if (psaGrade >= 9) badgeClass = 'high';
    else if (psaGrade < 7) badgeClass = 'low';

    results.innerHTML = `
        <div class="card">
            <div class="grade-result">
                <div>
                    <img src="${imageUrl}" class="grade-card-image" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22250%22 height=%22350%22><rect fill=%22%23171717%22 width=%22250%22 height=%22350%22/><text x=%22125%22 y=%22175%22 fill=%22%23525252%22 text-anchor=%22middle%22 font-size=%2248%22></text></svg>'">
                </div>
                <div>
                    <h3 style="margin-bottom: 0.5rem;">${data.card_name || 'Pokemon Card'}</h3>
                    <div style="color: var(--text-secondary); margin-bottom: 1.5rem;">${data.set_name || 'Unknown Set'}</div>

                    <h2>Estimated Grades</h2>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
                        <div>
                            <div style="font-size: 0.625rem; color: var(--text-muted); margin-bottom: 0.25rem;">PSA</div>
                            <span class="grade-badge ${badgeClass}">${grades.PSA || psaGrade}</span>
                        </div>
                        <div>
                            <div style="font-size: 0.625rem; color: var(--text-muted); margin-bottom: 0.25rem;">CGC</div>
                            <span class="grade-badge ${badgeClass}">${grades.CGC || (psaGrade - 0.5).toFixed(1)}</span>
                        </div>
                        <div>
                            <div style="font-size: 0.625rem; color: var(--text-muted); margin-bottom: 0.25rem;">BGS</div>
                            <span class="grade-badge ${badgeClass}">${grades.BGS || (psaGrade - 0.5).toFixed(1)}</span>
                        </div>
                    </div>

                    <h2>Subgrades</h2>
                    <div class="grade-scores">
                        <div class="grade-score">
                            <div class="grade-score-value">${subgrades.centering || '9'}</div>
                            <div class="grade-score-label">Centering</div>
                        </div>
                        <div class="grade-score">
                            <div class="grade-score-value">${subgrades.corners || '9'}</div>
                            <div class="grade-score-label">Corners</div>
                        </div>
                        <div class="grade-score">
                            <div class="grade-score-value">${subgrades.edges || '9'}</div>
                            <div class="grade-score-label">Edges</div>
                        </div>
                        <div class="grade-score">
                            <div class="grade-score-value">${subgrades.surface || '9'}</div>
                            <div class="grade-score-label">Surface</div>
                        </div>
                    </div>

                    ${data.defects?.length ? `
                        <h2>Defects Found</h2>
                        <ul style="color: var(--red); font-size: 0.875rem; margin-bottom: 1rem;">
                            ${data.defects.map(d => `<li>${d}</li>`).join('')}
                        </ul>
                    ` : ''}

                    <h2>Recommendation</h2>
                    <div style="padding: 1rem; background: ${data.worth_grading ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem;">
                            ${data.worth_grading ? ' Worth Grading' : ' Not Worth Grading'}
                        </div>
                        <div style="font-size: 0.875rem; color: var(--text-secondary);">
                            ${data.recommendation || (data.worth_grading ? 'This card has good potential for a high grade.' : 'The potential grade may not justify grading costs.')}
                        </div>
                    </div>

                    ${data.estimated_values ? `
                        <h2>Estimated Values</h2>
                        <div class="price-grid">
                            <div class="price-item">
                                <span class="price-label">Raw</span>
                                <span class="price-value">$${data.estimated_values.raw || '??'}</span>
                            </div>
                            <div class="price-item">
                                <span class="price-label">PSA ${psaGrade}</span>
                                <span class="price-value">$${data.estimated_values['psa_' + psaGrade] || data.estimated_values.graded || '??'}</span>
                            </div>
                        </div>
                    ` : ''}

                    ${data.demo_mode ? `
                        <div style="margin-top: 1rem; padding: 0.75rem; background: rgba(234, 179, 8, 0.1); border-radius: 6px; font-size: 0.75rem; color: var(--text-secondary);">
                            Demo mode - Set ANTHROPIC_API_KEY or OPENAI_API_KEY for real AI analysis
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}
