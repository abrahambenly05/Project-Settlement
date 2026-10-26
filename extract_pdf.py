import re
from docling.document_converter import DocumentConverter

def clean_ocr_text(markdown_text):
    lines = markdown_text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = re.sub(r'[ \t]+', ' ', line)
        line = line.strip()
        cleaned_lines.append(line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    cleaned_text = re.sub(r'\n{3, }', '\n\n', cleaned_text)
    return cleaned_text
    
def convert_pdf_to_markdown(source_path, output_path="full_text.md"):
    converter = DocumentConverter()
    doc = converter.convert(source_path).document
    
    num_pages = doc.num_pages()
    
    markdown_parts = []
    for page_no in range(1, num_pages + 1):
        page_md = doc.export_to_markdown(page_no=page_no).strip()
        if not page_md:
            page_md = "(The pages contains no extractable text - it likely contains only images or scans.)"
        
        page_md = clean_ocr_text(page_md)
        
        if page_no == 1:
            markdown_parts.append(f"<!-- Page {page_no} -->\n{page_md}")
        else:
            markdown_parts.append(f"---\n\n<!-- Page {page_no} -->\n{page_md}")
    
    markdown_text = "\n\n".join(markdown_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    print(f"Done! {num_pages} pages successfully extracted. The results have been saved to {output_path}")
    return markdown_text

if __name__ == "__main__":
    SOURCE_PDF = "Absensi PT Nusatama Teknologi.pdf"
    convert_pdf_to_markdown(SOURCE_PDF, "full_text.md")