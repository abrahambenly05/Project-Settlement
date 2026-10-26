from parse_absensi import parse_file, print_results, EXTRACTORS
from extract_pdf import convert_pdf_to_markdown

MARKDOWN_PATH = "full_text.md"
SOURCE_PDF = "Absensi PT Nusatama Teknologi.pdf"

def main():
    convert_pdf_to_markdown(SOURCE_PDF, MARKDOWN_PATH)
    
    results = parse_file(MARKDOWN_PATH)
    
    print_results(results)
    
    summary = {}
    for r in results:
        tipe = r['tipe']
        summary[tipe] = summary.get(tipe, 0) + 1
        
    print("\nSummary of the number of pages by document type:")
    for type, total in summary.items():
        print(f" {type}: {total} pages")
        
if __name__ == "__main__":
    main()