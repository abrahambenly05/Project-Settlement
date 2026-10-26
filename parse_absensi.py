import re

def clean(s):
    """Hapus spasi berlebih & karakter aneh hasil OCR."""
    return re.sub(r'\s+', ' ', s).strip() if s else ''

def extract_field(pattern, text, group=1, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return clean(match.group(group)) if match else None

def extract_first(patterns, text, group=1):
    for pattern in patterns:
        value = extract_field(pattern, text, group=group)
        if value:
            return value
    return None

VENDOR = "PT. Nusatama Teknologi"

MONTHS = r'Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember'

def is_valid_name(value):
    value = clean(value)
    if not value:
        return False

    lowered = value.lower()
    blocked_words = (
        'pt.', 'nusatama', 'periode', 'project', 'departemen',
        'komplek', 'telp', 'fax', 'tangerang selatan', 'nama project',
    )
    if value.startswith('#') or any(word in lowered for word in blocked_words):
        return False
    if re.search(r'\d', value):
        return False
    return bool(re.search(r'[A-Za-z]', value))

LABEL_WORDS = (
    'nama', 'project', 'periode', 'departemen', 'nama project',
    'kelompok', 'npp', 'npp / nama', 'unit', 'time zone', 'vendor',
)

def extract_label_block(text, target_label, labels=LABEL_WORDS):
    target_label = target_label.lower()

    header_lines = []
    for line in text.splitlines():
        if line.strip().startswith('|'):
            break
        header_lines.append(clean(line))

    other_labels = [w for w in labels if w != target_label]
    stop_pattern = None
    if other_labels:
        stop_pattern = re.compile(
            r'\s+(?:' + '|'.join(re.escape(w) for w in other_labels) + r')\s*[：:]',
            re.IGNORECASE,
        )
    for line in header_lines:
        m = re.search(rf'\b{re.escape(target_label)}\s*[：:]\s*(.+)$', line, re.IGNORECASE)
        if m:
            value = m.group(1)
            if stop_pattern:
                value = stop_pattern.split(value, maxsplit=1)[0]
            value = clean(value)
            if value:
                return value

    pending = []
    for line in header_lines:
        if not line:
            continue
        bare_lower = line.rstrip(':').strip().lower()
        if bare_lower in labels:
            pending.append(bare_lower)
            continue
        if line.startswith(':'):
            value = clean(line.lstrip(':'))
            if pending:
                label = pending.pop(0)
                if label == target_label and value:
                    return value
            continue
        if pending:
            label = pending.pop(0)
            if label == target_label and line:
                return line

    return None

def normalize_period(value):
    value = clean(value)
    value = re.sub(r'\s*-\s*', ' - ', value)
    return clean(value)

def infer_periode_from_dates(text):
    matches = []
    for line in text.splitlines():
        line = clean(line)
        if not line or 'jakarta' in line.lower():
            continue

        if not line.startswith('|'):
            continue

        matches.extend(re.findall(
            rf'\d{{1,2}}\s+({MONTHS})\s+(\d{{4}})',
            line,
            re.IGNORECASE
        ))

    if not matches:
        return None

    periods = [f"{bulan} {tahun}" for bulan, tahun in matches]
    unique_periods = list(dict.fromkeys(periods))

    return unique_periods[0] if len(unique_periods) == 1 else f"{unique_periods[0]} s/d {unique_periods[-1]}"

def extract_name_from_signature(text):
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        next_line = lines[i + 1]
        if '(Karyawan)' not in next_line:
            continue

        cells = [clean(cell).strip('()') for cell in line.strip().strip('|').split('|')]
        for cell in cells:
            if is_valid_name(cell):
                return cell

    return None

def extract_name_after_label(text):
    lines = [clean(line) for line in text.splitlines()]
    
    for i, line in enumerate(lines):
        if line.lower() == "nama":
            for next_line in lines[i + 1:i + 12]:
                if not next_line:
                    continue
                if next_line.lower() in ("periode", "project", "nama project"):
                    continue
                if next_line.startswith(":"):
                    candidate = clean(next_line.lstrip(":"))
                    if is_valid_name(candidate):
                        return candidate
                    continue
                if is_valid_name(next_line):
                    return next_line

    return None

def detect_type(page_text):
    t = page_text.upper()
    if re.search(r'SURAT\s*PERINTAH\s*LEMBUR', t):
        return 'Form Lembur'
    if re.search(r'LAPORAN\s*KEHADIRAN\s*KARYAWAN', t):
        return 'DigiHC'
    if re.search(r'BERITA\s*ACARA', t):
        return 'Berita Acara'
    # Timesheet: kolom CHECK IN / CHECK OUT tapi bukan SPL dan bukan DigiHC
    if re.search(r'CHECK\s*IN', t) and re.search(r'CHECK\s*OUT', t):
        return 'Timesheet'
    return 'unknown'

def is_table_continuation(page_text):
    first_line = page_text.strip().split('\n', 1)[0].strip()
    return bool(re.match(r'^\|\s*\d+\s*\|', first_line))

def extract_timesheet(page_text):
    """
    Keypoint: nama, periode, vendor, total kehadiran
    Total kehadiran = jumlah baris yang Notes-nya WFO/WFH/In (hadir kerja)
    Vendor: PT. Nusatama Teknologi
    """
    
    nama = extract_label_block(page_text, 'Nama') or extract_first([
        r'Nama\s*\n\s*:(.+)',
        r'Nama\s*[：:]\s*(.+)',
    ], page_text) or extract_name_after_label(page_text) or extract_name_from_signature(page_text)
    
    periode = extract_first([
        r'Periode\s*\n\s*:(.+)',
        r'Periode\s*[：:]\s*(.+)',
        rf'Periode\s*:\s*(\d{{1,2}}\s+({MONTHS})\s+\d{{4}}\s*-\s*\d{{1,2}}\s+({MONTHS})\s+\d{{4}})',
        rf':\s*((?:\d{{1,2}}\s*-\s*\d{{1,2}}\s+)?(?:{MONTHS})\s+\d{{4}})',
    ], page_text) or infer_periode_from_dates(page_text)
    periode = normalize_period(periode) if periode else None
    
    vendor = VENDOR
    
    summary_match = re.search(r'Total\s*Days\s*in\s*\|\s*(\d+)', page_text, re.IGNORECASE)
    if summary_match:
        total_kehadiran = int(summary_match.group(1))
    else:
        total_kehadiran = 0
        for line in page_text.split('\n'):
            line = line.strip()
            m = re.match(r'^\|\s*\d+\s*\|(.+)\|\s*$', line)
            if not m:
                continue
            cells = [c.strip() for c in m.group(1).split('|')]
            if len(cells) < 2:
                continue
            checkin = cells[1]
            notes = cells[-1]
            if re.match(r'^\d{1,2}[:.]\d{2}$', checkin) and notes.upper() not in ('OFF', 'LIBUR', 'LIB'):
                total_kehadiran += 1

        if total_kehadiran == 0:
            for line in page_text.split('\n'):
                line = line.strip()
                if not line.startswith('|') or not re.search(r'\d{2}/\d{2}/\d{4}', line):
                    continue
                times = re.findall(r'\b\d{1,2}[:.]\d{1,2}\b', line)
                if len(times) >= 2:
                    total_kehadiran += 1
    
    return {
        'tipe': 'Timesheet',
        'nama': nama,
        'periode': periode,
        'vendor': vendor,
        'total_kehadiran': total_kehadiran,
    }
    
def extract_form_lembur(page_text):
    """
    Keypoint: nama, periode, vendor, jumlah hari lembur
    Vendor: PT. Nusatama Teknologi
    """
    nama = extract_label_block(page_text, 'Nama') or extract_first([
        r'Nama\s*\n\s*:(.+)',
        r'Nama\s*[：:]\s*(.+)',
        r'\|\s*Nama\s*\|\s*:?\s*([^|]+)',
    ], page_text) or extract_name_after_label(page_text)

    periode = extract_first([
        r'Periode\s*\n\s*:(.+)',
        r'Periode\s*[：:]\s*(.+)',
        r'\|\s*Periode\s*\|\s*:?\s*([^|]+)',
    ], page_text) or infer_periode_from_dates(page_text)
    periode = normalize_period(periode) if periode else None

    vendor = VENDOR

    spl_rows = re.findall(
        r'\|\s*\d+\s*\|\s*[\w/ ,]+\d{4}',   # "| 1 | 10 Februari 2026 ..." 
        page_text
    )
    jumlah_lembur = len(spl_rows)
    
    return {
        'tipe': 'Form Lembur',
        'nama': nama,
        'periode': periode,
        'vendor': vendor,
        'jumlah_hari_lembur': jumlah_lembur,
    }
    
def extract_berita_acara(page_text):
    """
    Keypoint: nama, periode, vendor, jumlah ketidakhadiran
    Periode di-infer dari rentang tanggal dalam tabel.
    Vendor : PT. Nusatama Teknologi
    """
    nama = extract_label_block(page_text, 'Nama') or extract_first([
        r'Nama\s*[：:]\s*\n\s*(.+)',
        r'Nama\s*\n?\s*[：:]\s*(.+)',
    ], page_text) or extract_name_after_label(page_text)

    kelompok = extract_field(r'Kelompok\s*\n?\s*[：:]\s*(.+)', page_text)
    npp      = extract_field(r'NPP\s*[：:]\s*(.+)', page_text)
    
    rows = re.findall(
        r'\|\s*\d{1,2}\s+\w+\s+\d{4}\s*\|',
        page_text
    )
    
    jumlah_ketidakhadiran = len(rows)
    
    bulan_list = re.findall(r'\d{1,2}\s+(\w+\s+\d{4})', page_text)
    if bulan_list:
        bulan_unik = list(dict.fromkeys(bulan_list))
        periode = bulan_unik[0] if len(bulan_unik) == 1 else f"{bulan_unik[0]} s/d {bulan_unik[-1]}"
    else:
        periode = None
    
    return {
        'tipe' : 'Berita Acara',
        'nama' : nama,
        'periode' : periode,
        'vendor' : VENDOR,
        'jumlah_ketidakhadiran' : jumlah_ketidakhadiran,
    }
    
def extract_digihc(page_text):
    """
    Keypoint: nama, periode, vendor, jumlah H, T, TK
    DigiHC = Laporan Kehadiran Karyawan dari Nusatama Teknologi
    Vendor: PT. Nusatama Teknologi
    """
    raw_npp_nama = extract_label_block(page_text, 'npp / nama')
    nama = None
    if raw_npp_nama:
        m = re.match(r'^\S+\s+(.+)$', raw_npp_nama)
        nama = clean(m.group(1)) if m else clean(raw_npp_nama)
    if not nama:
        nama = extract_field(r'NPP[/\s]*Nama\s*\n?\s*[：:]\s*OM\w+\s+(.+)', page_text)
    if not nama:
        nama = extract_field(r'NPP[/\s]*Nama\s*[：:]\s*OM\w+\s+(.+)', page_text)

    unit = extract_field(r'Unit\s*\n?\s*[：:]\s*(.+)', page_text)
    
    bulan_list = re.findall(r'\d{2}\s+(\w+\s+\d{4})', page_text)
    if bulan_list:
        bulan_unik = list(dict.fromkeys(bulan_list))
        periode = bulan_unik[0] if len(bulan_unik) == 1 else f"{bulan_unik[0]} s/d {bulan_unik[-1]}"
    else:
        periode = None
    
    ket_values = re.findall(r'^\|\s*[^|]+\|\s*\d{2}\s+\w+\s+\d{4}\s*\|.*\|\s*(H|T|TK|LIB|SK\s*\d*|S)\s*\|\s*$', page_text, re.MULTILINE)
    jumlah_H = ket_values.count('H')
    jumlah_T = ket_values.count('T')
    jumlah_TK = ket_values.count('TK')
    
    return {
        'tipe' : 'DigiHC',
        'nama' : nama,
        'periode' : periode,
        'vendor' : VENDOR,
        'jumlah_H' : jumlah_H,
        'jumlah_T' : jumlah_T,
        'jumlah_TK' : jumlah_TK,
    }

EXTRACTORS = {
    'Timesheet': extract_timesheet,
    'Form Lembur': extract_form_lembur,
    'Berita Acara': extract_berita_acara,
    'DigiHC': extract_digihc,
}

def parse_pages(pages):
    results = []
    last_type = None
    last_context = {}

    for i, page in enumerate(pages, start=1):
        doc_type = detect_type(page)
        continuation_mode = None

        if doc_type == 'unknown' and last_type is not None:
            if is_table_continuation(page):
                doc_type = last_type
                continuation_mode = 'table'
            elif last_type == 'Berita Acara':
                doc_type = last_type
                continuation_mode = 'attachment'

        if doc_type in EXTRACTORS:
            data = EXTRACTORS[doc_type](page)
        else:
            data = {'tipe': 'Unknown'}
            
        if doc_type in EXTRACTORS:
            for key in ('nama', 'periode', 'vendor'):
                if not data.get(key):
                    data[key] = last_context.get(key)

        if continuation_mode == 'table':
            for key in ('nama', 'periode', 'vendor'):
                if not data.get(key):
                    data[key] = last_context.get(key)
        elif continuation_mode == 'attachment':
            for key in ('nama', 'periode', 'vendor', 'jumlah_ketidakhadiran'):
                data[key] = last_context.get(key, data.get(key))

        if doc_type in EXTRACTORS:
            last_type = doc_type
            last_context = dict(data)

        data['page'] = i
        results.append(data)

    return results

def load_pages(filepath):
    text = open(filepath, "r", encoding="utf-8").read()
    pages = re.split(r'<!--\s*Page\s+\d+\s*-->', text)
    return [p.strip() for p in pages if p.strip()]

def parse_file(filepath):
    pages = load_pages(filepath)
    return parse_pages(pages)

def print_results(results):
    for r in results:
        print("=" * 60)
        print(f" Halaman : {r['page']}")
        print(f" Tipe Dokumen : {r['tipe']}")
        if r['tipe'] == 'Unknown':
            continue
        print(f" Nama : {r.get('nama')}")
        print(f" Periode : {r.get('periode')}")
        print(f" Vendor : {r.get('vendor')}")
        if r['tipe'] == 'Timesheet':
            print(f" Total Kehadiran : {r.get('total_kehadiran')}")
        elif r['tipe'] == 'Form Lembur':
            print(f" Jumlah Hari Lembur : {r.get('jumlah_hari_lembur')}")
        elif r['tipe'] == 'Berita Acara':
            print(f" Jumlah Ketidakhadiran : {r.get('jumlah_ketidakhadiran')}")
        elif r['tipe'] == 'DigiHC':
            print(f" Jumlah H : {r.get('jumlah_H')}")
            print(f" Jumlah T : {r.get('jumlah_T')}")
            print(f" Jumlah TK : {r.get('jumlah_TK')}")
    print("=" * 60)
    
if __name__ == "__main__":
    results = parse_file("full_text.md")
    print_results(results)