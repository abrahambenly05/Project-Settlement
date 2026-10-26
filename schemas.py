from typing import Dict, List, Optional
from pydantic import BaseModel

class PageResult(BaseModel):
    page: int
    tipe: str
    nama: Optional[str] = None
    periode: Optional[str] = None
    vendor: Optional[str] = None
    total_kehadiran: Optional[int] = None
    jumlah_hari_lembur: Optional[int] = None
    jumlah_ketidakhadiran: Optional[int] = None
    jumlah_H: Optional[int] = None
    jumlah_T: Optional[int] = None
    jumlah_TK: Optional[int] = None

class EmployeeSummary(BaseModel):
    nama: str
    tipe_dokumen: List[str]
    periode: List[str]          # semua variasi periode yang ditemukan (berguna deteksi anomali)
    vendor: Optional[str] = None
    total_kehadiran: Optional[int] = None
    jumlah_hari_lembur: Optional[int] = None
    jumlah_ketidakhadiran: Optional[int] = None
    jumlah_H: Optional[int] = None
    jumlah_T: Optional[int] = None
    jumlah_TK: Optional[int] = None
    pages: List[int]

class ExtractResponse(BaseModel):
    filename: str
    num_pages: int
    summary: Dict[str, int]
    results: List[PageResult]
    by_employee: Dict[str, EmployeeSummary]