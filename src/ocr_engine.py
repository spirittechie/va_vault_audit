import os
import sys
import argparse
import logging
from typing import List, Dict, Tuple

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def is_scanned_page(page: fitz.Page, text_threshold: int = 30) -> bool:
    """
    Determine if a page is scanned/image-only by checking text length.
    If the extracted text length is below threshold, treat as scanned.
    """
    text = page.get_text("text").strip()
    if len(text) < text_threshold:
        return True
    return False


def ocr_image(image: Image.Image, lang: str = "eng") -> Tuple[str, float]:
    """
    Perform OCR on a PIL Image and return extracted text and average confidence.
    """
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    texts = []
    confidences = []
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        txt = data["text"][i].strip()
        conf = int(data["conf"][i])
        if txt:
            texts.append(txt)
            confidences.append(conf)
    avg_conf = float(sum(confidences)) / len(confidences) if confidences else 0.0
    full_text = " ".join(texts)
    return full_text, avg_conf


def extract_text_from_pdf(
    input_path: str,
    output_path: str,
    lang: str = "eng"
) -> str:
    """
    Extract text from a PDF file, using OCR for scanned pages.
    Saves output to a .txt file at output_path and returns the text.
    """
    logger.info(f"Processing PDF: {input_path}")
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        logger.error(f"Failed to open {input_path}: {e}")
        return ""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    results: List[str] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_number = page_num + 1
        try:
            if is_scanned_page(page):
                logger.info(f"Page {page_number}: detected as scanned, performing OCR.")
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text, conf = ocr_image(img, lang)
                logger.info(f"Page {page_number}: OCR confidence avg={conf:.2f}")
            else:
                text = page.get_text("text")
                conf = None
                logger.info(f"Page {page_number}: extracted text n_chars={len(text)}")
            if not text.strip():
                logger.warning(f"Page {page_number}: no text extracted (skipped)")
            results.append(text)
        except Exception as e:
            logger.error(f"Page {page_number}: error during extraction: {e}")

    full_text = "\n\n".join(results)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        logger.info(f"Saved extracted text to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save text file {output_path}: {e}")

    return full_text


def process_input(
    input_path: str,
    output_dir: str,
    lang: str = "eng"
) -> Dict[str, str]:
    """
    Handle input which can be a file or directory, extract text for each PDF.
    Returns a mapping of input PDF paths to extracted text.
    """
    extracted: Dict[str, str] = {}
    if os.path.isdir(input_path):
        for fname in os.listdir(input_path):
            if fname.lower().endswith(".pdf"):
                in_pdf = os.path.join(input_path, fname)
                out_txt = os.path.join(output_dir, os.path.splitext(fname)[0] + ".txt")
                text = extract_text_from_pdf(in_pdf, out_txt, lang)
                extracted[in_pdf] = text
    elif os.path.isfile(input_path) and input_path.lower().endswith(".pdf"):
        fname = os.path.basename(input_path)
        out_txt = os.path.join(output_dir, os.path.splitext(fname)[0] + ".txt")
        text = extract_text_from_pdf(input_path, out_txt, lang)
        extracted[input_path] = text
    else:
        logger.error(f"Invalid input: {input_path} is not a PDF file or directory")
    return extracted


def main():
    parser = argparse.ArgumentParser(
        description="OCR engine for scanned PDF text extraction using Tesseract"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input PDF file or directory containing PDFs"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory for extracted text files"
    )
    parser.add_argument(
        "--language", "-l",
        default="eng",
        help="Language for Tesseract OCR (e.g., eng, spa)"
    )
    args = parser.parse_args()

    results = process_input(args.input, args.output, args.language)
    logger.info(f"Extraction complete for {len(results)} document(s)")


if __name__ == "__main__":
    main()
