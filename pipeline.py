import os
import re
import tempfile
from collections import Counter, OrderedDict

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from extract_pdf import convert_pdf_to_markdown
from parse_absensi import parse_file
from schemas import EmployeeSummary, ExtractResponse, PageResult

def normalize_nama(nama: str) -> str | None:
    if not nama:
        return None
    nama = re.sub(r'\(.*?\)', '', nama)
    nama = re.sub(r'\s+', ' ', nama).strip()
    return nama.upper() if nama else None

def aggregate_by_nama(page_results: list[PageResult]) -> dict[str, EmployeeSummary]:
    groups: "OrderedDict[str, dict]" = OrderedDict()

    for r in page_results:
        key = normalize_nama(r.nama)
        if not key:
            continue  
        if key not in groups:
            groups[key] = {
                "nama": r.nama,  
                "tipe_dokumen": [],
                "periode": [],
                "vendor": r.vendor,
                "total_kehadiran": 0,
                "jumlah_hari_lembur": 0,
                "jumlah_ketidakhadiran": 0,
                "jumlah_H": 0,
                "jumlah_T": 0,
                "jumlah_TK": 0,
                "pages": [],
            }

        g = groups[key]
        if r.tipe not in g["tipe_dokumen"]:
            g["tipe_dokumen"].append(r.tipe)
        if r.periode and r.periode not in g["periode"]:
            g["periode"].append(r.periode)
        g["pages"].append(r.page)
        
        if r.total_kehadiran is not None:
            g["total_kehadiran"] += r.total_kehadiran
        if r.jumlah_hari_lembur is not None:
            g["jumlah_hari_lembur"] += r.jumlah_hari_lembur
        if r.jumlah_ketidakhadiran is not None:
            g["jumlah_ketidakhadiran"] = r.jumlah_ketidakhadiran
        if r.jumlah_H is not None:
            g["jumlah_H"] += r.jumlah_H
        if r.jumlah_T is not None:
            g["jumlah_T"] += r.jumlah_T
        if r.jumlah_TK is not None:
            g["jumlah_TK"] += r.jumlah_TK

    return {
        key: EmployeeSummary(
            nama=g["nama"],
            tipe_dokumen=g["tipe_dokumen"],
            periode=g["periode"],
            vendor=g["vendor"],
            total_kehadiran=g["total_kehadiran"] or None,
            jumlah_hari_lembur=g["jumlah_hari_lembur"] or None,
            jumlah_ketidakhadiran=g["jumlah_ketidakhadiran"] or None,
            jumlah_H=g["jumlah_H"] or None,
            jumlah_T=g["jumlah_T"] or None,
            jumlah_TK=g["jumlah_TK"] or None,
            pages=sorted(g["pages"]),
        )
        for key, g in groups.items()
    }

async def run_keypoint_extraction(filename: str, contents: bytes) -> ExtractResponse:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        md_path = os.path.join(tmpdir, "full_text.md")

        with open(pdf_path, "wb") as f:
            f.write(contents)

        markdown_text = await _run_ocr(pdf_path, md_path)
        raw_results = await _run_parsing(md_path)

        page_results = [PageResult(**r) for r in raw_results]
        summary = dict(Counter(r.tipe for r in page_results))
        by_employee = aggregate_by_nama(page_results)

        return ExtractResponse(
            filename=filename,
            num_pages=len(page_results),
            summary=summary,
            results=page_results,
            by_employee=by_employee, 
        )

async def _run_ocr(pdf_path: str, md_path: str) -> str:
    try:
        markdown_text = await run_in_threadpool(convert_pdf_to_markdown, pdf_path, md_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal proses PDF: {e}")

    if not markdown_text.strip():
        raise HTTPException(status_code=422, detail="Tidak ada yang berhasil diekstrak dari PDF")

    return markdown_text

async def _run_parsing(md_path: str) -> list:
    try:
        raw_results = await run_in_threadpool(parse_file, md_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal parsing hasil OCR: {e}")

    if not raw_results:
        raise HTTPException(status_code=422, detail="Tidak ada halaman yang berhasil diparsing")

    return raw_results