Extrair PDF -> Excel

Uso

- GUI mode: dar duplo clique em `extrair_pdf_excel.exe` e selecionar a pasta.
- CLI mode: `extrair_pdf_excel.exe <pasta>` ou `python extrair_pdf_excel.py <pasta>`.

Output

- Gera `resultado.xlsx` na pasta selecionada com colunas: Ficheiro, RefPagamento, ValorSemIVA, ValorComIVA, PT2, DescricaoDebito, NeedsReview

Requisitos

Instalar dependências via:

```powershell
pip install -r requirements.txt
```

Construir EXE

```powershell
py -m PyInstaller --onefile --windowed --name extrair_pdf_excel "extrair_pdf_excel.py"
```

Observações

- O script usa PyMuPDF (`fitz`) para extrair texto. Para PDFs escaneados habilitar OCR instalando `pdf2image` e `pytesseract` e certificando que `tesseract` está disponível no PATH.
- `NeedsReview` é marcado quando `ValorSemIVA` ou `ValorComIVA` estiverem em falta ou quando `ValorComIVA < ValorSemIVA`.
