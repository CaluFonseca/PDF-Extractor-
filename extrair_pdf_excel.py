import os
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import pandas as pd

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

import argparse
import logging


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_money(value: str):
    if not value:
        return ""
    value = value.strip().replace("€", "").replace(" ", "")

    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif "." in value and re.fullmatch(r"\d{1,3}(\.\d{3})+", value):
        value = value.replace(".", "")

    return value


def find_first_match(text: str, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def find_value_near_keyword(text: str, keywords):
    text = normalize_text(text)
    for kw in keywords:
        pattern = rf"{re.escape(kw)}.*?(\d{{1,3}}(?:[.\s]\d{{3}})*,\d{{2}}|\d+(?:[.,]\d{{2}}))"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_money(match.group(1))
    return ""


def clean_comment_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip(" -:;")
    value = re.split(
        r"\s*(?:Data\s+da\b|Data\s+de\s+vencimento\b|Data\s+da\s+condi[çc]ã[oõ]\b|Vencimento\b|Condi[çc]ã[oõ]\b|Prazo\b|Prazos\b|Pagamento\s+at[eé]\b)",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    value = re.split(r"\s*(?:\d{1,2}/\d{1,2}/\d{2,4})\s*$", value, maxsplit=1)[0]
    value = value.strip(" -:;.,")
    return value[:300]


def find_description(text: str):
    text = normalize_text(text)
    patterns = [
        r"(?:coment[aá]rios?|observa[çc]õ[eé]s?|observacoes|comentario|coment[áa]rio de debito|coment[áa]rio).*?(?:[:\-])\s*(.{0,220})",
        r"(?:coment[aá]rios?|observa[çc]õ[eé]s?|observacoes|comentario).*?(.{0,220})"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            value = clean_comment_text(value)
            if value and len(value) > 2 and not re.fullmatch(r"[A-Z0-9\-_/., ]+", value):
                return value

    return ""


def find_bruto_total(text: str, sem_iva: str = ""):
    text = normalize_text(text)
    patterns = [
        r"valor\s+bruto.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"valor\s+total.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"total\s+montante.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"total\s+factura.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"total\s+geral.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"com\s+iva.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
        r"valor\s+c/?\s*iva.*?(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            start = match.end()
            window = text[start:start + 500]
            nums = re.findall(r"(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))", window)
            norm_vals = []
            for n in nums:
                nv = normalize_money(n)
                try:
                    norm_vals.append(float(nv))
                except Exception:
                    continue

            if norm_vals:
                eur_match = re.search(r"\bEUR\b", window)
                if eur_match:
                    segment = window[:eur_match.start()]
                    seg_nums = re.findall(r"(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))", segment)
                    seg_vals = []
                    for n in seg_nums:
                        nv = normalize_money(n)
                        try:
                            seg_vals.append(float(nv))
                        except Exception:
                            continue
                    if seg_vals:
                        if sem_iva:
                            try:
                                sem_num = float(sem_iva)
                                candidates = [v for v in seg_vals if v > sem_num and v < 1e7]
                                if candidates:
                                    return f"{max(candidates):.2f}"
                            except Exception:
                                pass
                        return f"{seg_vals[-1]:.2f}"

                if sem_iva:
                    try:
                        sem_num = float(sem_iva)
                        candidates = [v for v in norm_vals if v > sem_num and v < 1e7]
                        if candidates:
                            return f"{max(candidates):.2f}"
                    except Exception:
                        pass

                return f"{norm_vals[-1]:.2f}"

            return normalize_money(match.group(1))

    matches = re.findall(r"(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))", text)
    if matches:
        values = [float(normalize_money(v)) for v in matches if normalize_money(v)]
        if sem_iva:
            sem_iva_num = float(sem_iva)
            values = [v for v in values if v > sem_iva_num]
        if values:
            return f"{max(values):.2f}"
    return ""


def extract_from_text(raw_text: str):
    text = normalize_text(raw_text)
    ref = find_first_match(text, [r"Q00\d{5,}", r"Q00[0-9A-Z-]+"])
    pt2 = find_first_match(text, [r"PT2[0-9A-Z-]+", r"PT2\d{5,}"])

    valor_sem_iva = find_value_near_keyword(text, [
        "valor sem iva", "sem iva", "s/ iva", "valor s/ iva", "total sem iva",
        "base imponivel", "base", "montante sem iva"
    ])

    bruto_val = find_bruto_total(text, valor_sem_iva)
    if bruto_val:
        valor_com_iva = bruto_val
    elif valor_sem_iva:
        valor_com_iva = valor_sem_iva
    else:
        valor_com_iva = ""

    if not valor_sem_iva:
        matches = re.findall(r"(?:€\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+(?:[.,]\d{2}))", text)
        if matches:
            values = [normalize_money(v) for v in matches]
            valor_sem_iva = values[0]
            if not valor_com_iva and len(values) > 1:
                valor_com_iva = max(values)

    descricao = find_description(text)
    if not descricao and pt2:
        descricao = pt2

    return {
        "RefPagamento": ref,
        "ValorSemIVA": valor_sem_iva,
        "ValorComIVA": valor_com_iva,
        "PT2": pt2,
        "DescricaoDebito": descricao,
    }


def extract_pdf_text(path: str):
    if fitz is None:
        raise RuntimeError("PyMuPDF não está instalado.")

    doc = fitz.open(path)
    text = ""
    try:
        for page in doc:
            text += " " + page.get_text("text")
    finally:
        doc.close()

    return text


def ocr_pdf(path: str):
    if convert_from_path is None or pytesseract is None:
        raise RuntimeError("OCR não disponível. Instale pdf2image e pytesseract.")

    images = convert_from_path(path)
    text = ""
    for image in images:
        text += " " + pytesseract.image_to_string(image, lang="por")
    return text


def process_pdf(path: str):
    try:
        text = extract_pdf_text(path)
        if not text or len(text.strip()) < 20:
            text = ocr_pdf(path)
    except Exception:
        try:
            text = ocr_pdf(path)
        except Exception:
            text = ""

    return extract_from_text(text)


def run_processing(folder_path: str):
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {folder}")

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Nenhum ficheiro PDF encontrado em: {folder}")

    rows = []
    for pdf in pdf_files:
        info = process_pdf(str(pdf))
        needs_review = False
        try:
            vs = info.get("ValorSemIVA", "")
            vc = info.get("ValorComIVA", "")
            if not vs or not vc:
                needs_review = True
            else:
                try:
                    if float(vc) < float(vs):
                        needs_review = True
                except Exception:
                    needs_review = True
        except Exception:
            needs_review = True

        rows.append({
            "Ficheiro": pdf.name,
            "RefPagamento": info.get("RefPagamento", ""),
            "ValorSemIVA": info.get("ValorSemIVA", ""),
            "ValorComIVA": info.get("ValorComIVA", ""),
            "PT2": info.get("PT2", ""),
            "DescricaoDebito": info.get("DescricaoDebito", ""),
            "NeedsReview": needs_review,
        })

    output = folder / "resultado.xlsx"
    df = pd.DataFrame(rows)
    df.to_excel(output, index=False)
    return output


def select_folder_and_process():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Seleciona a pasta com os PDFs")
    if not folder:
        messagebox.showinfo("Cancelar", "Nenhuma pasta selecionada.")
        return

    try:
        output_file = run_processing(folder)
        messagebox.showinfo(
            "Concluído",
            f"Processados com sucesso.\n\nExcel criado em:\n{output_file}"
        )
    except Exception as exc:
        messagebox.showerror("Erro", f"Não foi possível processar os PDFs.\n\n{exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai campos de PDFs para Excel")
    parser.add_argument("folder", nargs="?", help="Pasta com PDFs (se omitido abre GUI)")
    args = parser.parse_args()

    try:
        if args.folder:
            logging.info(f"Processando pasta: {args.folder}")
            out = run_processing(args.folder)
            print(out)
        else:
            select_folder_and_process()
    except Exception as exc:
        logging.exception("Erro crítico")
        if not args.folder:
            messagebox.showerror("Erro crítico", str(exc))
        sys.exit(1)
