const dropzone = document.getElementById('dropzone');
const fileRow = document.getElementById('file-row');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const fcName = document.getElementById('fc-name');
const fcSize = document.getElementById('fc-size');
const actionsRow = document.getElementById('actions-row');
const processBtn = document.getElementById('process-btn');
const cancelBtn = document.getElementById('cancel-btn');
const resetBtn = document.getElementById('reset-btn');
const progressFill = document.getElementById('progress-fill');
const fstatus = document.getElementById('fstatus');
const errorCard = document.getElementById('error-card');
const errorBox = document.getElementById('error-box');
const resultCard = document.getElementById('result-card');
const apiURLInput = document.getElementById('api-url');

let selectedFile = null;

function fmtSize(bytes) {
    if(bytes < 1024) return bytes + ' B';
    if(bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
    return (bytes/1024/1024).toFixed(2) + ' MB';
}

function showFile(file) {
    selectedFile = file;
    fileRow.classList.remove('hidden', 'err');
    fcName.textContent = file.name;
    fcSize.textContent = fmtSize(file.size);
    progressFill.style.width = '0%';
    fstatus.textContent = 'Ready to Upload';
    fstatus.className = 'fstatus';
    actionsRow.classList.remove('hidden');
    errorCard.classList.add('hidden');
    resultCard.classList.add('hidden');
}

function resetDropZone() {
    selectedFile = null;
    fileInput.value = '';
    fileRow.classList.add('hidden');
    actionsRow.classList.add('hidden');
    progressFill.style.width = '0%';
    processBtn.disabled = false;
    processBtn.textContent = 'Process Document';
}

browseBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
    if(fileInput.files[0]) showFile(fileInput.files[0]);
});

['dragenter', 'dragover'].forEach(evt => 
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('drag'); })
);
['dragleave', 'drop'].forEach(evt => 
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('drag'); })
);
dropzone.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    if(file) showFile(file);
});

cancelBtn.addEventListener('click', resetDropZone);
resetBtn.addEventListener('click', () => {
    resetDropZone();
    resultCard.classList.add('hidden');
});

processBtn.addEventListener('click', () => {
    if(!selectedFile) return;
    if(!selectedFile.name.toLowerCase().endsWith('.pdf')){
        showError('Only PDF files are supported.');
        return;
    }

    errorCard.classList.add('hidden');
    resultCard.classList.add('hidden');
    fileRow.classList.remove('err');
    processBtn.disabled = true;
    processBtn.textContent = 'Processing...';
    fstatus.className = 'fstatus';
    fstatus.textContent = 'Uploading... 0%';

    const formData = new FormData();
    formData.append('file', selectedFile);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', apiURLInput.value, true);
    xhr.responseType = 'json';

    xhr.upload.onprogress = (e) => {
        if(e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            progressFill.style.width = pct + '%';
            fstatus.textContent = pct < 100 ? 'Uploading... ' + pct + '%' : 'Running OCR & parsing on server...';
        }
    };

    xhr.onload = () => {
        processBtn.disabled = false;
        processBtn.textContent = 'Process Document';
        if (xhr.status === 200) {
            fstatus.textContent = 'Done';
            fstatus.className = 'fstatus fstatus-done';
            renderResult(xhr.response);
        } else {
            const detail = (xhr.response && xhr.response.detail) ? xhr.response.detail : xhr.statusText;
            fstatus.textContent = 'Failed';
            fstatus.className = 'fstatus fstatus-err';
            fileRow.classList.add('err');
            showError(detail, xhr.status);
        }
    };

    xhr.onerror = () => {
        processBtn.disabled = false;
        processBtn.textContent = 'Process Document';
        fstatus.textContent = 'Failed';
        fstatus.className = 'fstatus fstatus-err';
        fileRow.classList.add('err');
        showError('Could not reach the server. Make sure uvicorn is running and CORS is enabled in FastAPI.');
    };

    xhr.send(formData);
});

function showError(message, status) {
    resultCard.classList.add('hidden');
    errorCard.classList.remove('hidden');
    errorBox.innerHTML = '<b>' + (status ? 'Error ' + status : 'Error') + '</b>' + message;
}

const TIPE_METRIC = {
    'Timesheet': r => r.total_kehadiran != null ? r.total_kehadiran + ' hari hadir' : '-',
    'Form Lembur': r => r.jumlah_hari_lembur != null ? r.jumlah_hari_lembur + ' hari lembur' : '-',
    'Berita Acara': r => r.jumlah_ketidakhadiran != null ? r.jumlah_ketidakhadiran + ' hari absen' : '-',
    'DigiHC': r => (r.jumlah_H ?? 0) + ' H / ' + (r.jumlah_T ?? 0) + ' T / ' + (r.jumlah_TK ?? 0) + ' TK',
};

function renderResult(data) {
    errorCard.classList.add('hidden');
    resultCard.classList.remove('hidden');

    document.getElementById('badge-ok').textContent = '✓ ' + data.num_pages + ' pages processed';
    document.getElementById('result-file').textContent = data.filename;

    const vendorEl = document.getElementById('result-vendor');
    const vendorValue = (data.results || []).find(r => r.vendor)?.vendor;
    vendorEl.textContent = vendorValue ? 'Vendor: ' + vendorValue : '';

    const chipsEl = document.getElementById('result-chips');
    chipsEl.innerHTML = '';
    Object.entries(data.summary || {}).forEach(([tipe, count]) => {
        const c = document.createElement('span');
        c.className = 'chip';
        c.textContent = tipe + ' . ' + count;
        chipsEl.appendChild(c);
    });

    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';
    (data.results || []).forEach(r => {
        const tr = document.createElement('tr');
        const metricFn = TIPE_METRIC[r.tipe];
        tr.innerHTML = 
            '<td class="mono">' + r.page + '</td>' +
            '<td><span class="tipe-badge">' + r.tipe + '</span></td>' +
            '<td>' + (r.nama || '-') + '</td>' +
            '<td class="mono">' + (r.periode || '-') + '</td>' +
            '<td class="mono">' + (metricFn ? metricFn(r) : '-') + '</td>';
        tbody.appendChild(tr); 
    });

    const empList = document.getElementById('employee-list');
    empList.innerHTML = '';
    Object.values(data.by_employee || {}).forEach(emp => {
        const div = document.createElement('div');
        div.className = 'emp-card';

        let badges = (emp.tipe_dokumen || []).map(t => '<span class="tipe-badge">' + t + '</span>').join('');

        let metrics = '';
        const metricDefs = [
            ['total_kehadiran','Hadir'], ['jumlah_hari_lembur', 'Lembur'],
            ['jumlah_ketidakhadiran', 'Absen'], ['jumlah_H', 'H'], ['jumlah_T', 'T'], ['jumlah_TK', 'TK']
        ];
        metricDefs.forEach(([key,label]) => {
            if(emp[key] != null){
                metrics += '<div class="metric"><div class="v">' + emp[key] + '</div><div class="l">' + label + '</div></div>';
            } 
        });

        let periodeWarn = '';
        if(emp.periode && emp.periode.length > 1){
            periodeWarn = '<div class="period-warn">⚠ Inconsistent periode: ' + emp.periode.join(' vs ') + '</div>';
        }

        div.innerHTML =
            '<div class="emp-head">' +
                '<div class="emp-name">' + emp.nama + '</div>' +
                '<div class="emp-pages">page ' + (emp.pages || []).join(', ') + '</div>' +
            '</div>' +
            '<div class="emp-badges">' + badges + '</div>' +
            '<div class="emp-metrics">' + metrics + '</div>' +
            periodeWarn;
            
        empList.appendChild(div);
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.panel).classList.add('active');
        };
    });
}