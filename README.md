PDF -> Excel Extractor

Usage

- GUI mode: double-click `extrair_pdf_excel.exe` and select the folder containing PDFs.
- CLI mode: `extrair_pdf_excel.exe <folder>` or `python extrair_pdf_excel.py <folder>`.

Output

- Produces `resultado.xlsx` in the selected folder with columns: Ficheiro, RefPagamento, ValorSemIVA, ValorComIVA, PT2, DescricaoDebito, NeedsReview

Requirements

Install Python dependencies with:

```powershell
pip install -r requirements.txt
```

Build the Windows executable

```powershell
py -m PyInstaller --onefile --windowed --name extrair_pdf_excel "extrair_pdf_excel.py"
```

Notes

- The script uses PyMuPDF (`fitz`) for text extraction. For scanned PDFs enable OCR by installing `pdf2image` and `pytesseract` and ensuring `tesseract` is available in PATH.
- `NeedsReview` is set when `ValorSemIVA` or `ValorComIVA` are missing or when `ValorComIVA < ValorSemIVA`.
