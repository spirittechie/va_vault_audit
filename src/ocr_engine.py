import os
import argparse
import logging
from typing import Optional, List

try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError as e:
    logging.error("Missing required OCR dependencies: %s", e)
    raise

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)


def extract_text_from_pdf(pdf_path: str, language: str = 'eng') -> str:
    """
    Extracts text from a single PDF file using Tesseract OCR.
    """
    logging.info("Starting OCR for %s (lang=%s)", pdf_path, language)
    try:
        images = convert_from_path(pdf_path)
    except Exception as e:
        logging.error("Failed to convert PDF to images: %s", e)
        raise

    text_pages: List[str] = []
    for i, page in enumerate(images, start=1):
        try:
            page_text = pytesseract.image_to_string(page, lang=language)
            text_pages.append(page_text)
            logging.debug("Extracted text from page %d of %s", i, pdf_path)
        except Exception as e:
            logging.error("OCR failed on page %d of %s: %s", i, pdf_path, e)

    full_text = "\n\n".join(text_pages)
    logging.info("Completed OCR for %s, extracted %d pages", pdf_path, len(images))
    return full_text


def process_input(input_path: str, output_path: Optional[str], language: str):
    """
    Processes a single PDF or all PDFs in a directory, writing text outputs.
    """
    if os.path.isdir(input_path):
        if output_path and not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        pdf_files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith('.pdf')
        ]
        logging.info("Found %d PDF files in directory %s", len(pdf_files), input_path)
        for pdf in pdf_files:
            basename = os.path.splitext(os.path.basename(pdf))[0]
            out_file = (
                os.path.join(output_path, basename + '.txt')
                if output_path else
                os.path.join(os.path.dirname(pdf), basename + '.txt')
            )
            text = extract_text_from_pdf(pdf, language)
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(text)
            logging.info("Wrote OCR output to %s", out_file)
    else:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        if output_path:
            if output_path.lower().endswith('.txt'):
                out_file = output_path
            else:
                os.makedirs(output_path, exist_ok=True)
                out_file = os.path.join(output_path, basename + '.txt')
        else:
            out_file = os.path.join(os.path.dirname(input_path), basename + '.txt')

        text = extract_text_from_pdf(input_path, language)
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(text)
        logging.info("Wrote OCR output to %s", out_file)


def main(
    input_path: str = 'docs/sample.pdf',
    output_path: str = 'docs/sample_ocr.txt',
    language: str = 'eng'
) -> str:
    """
    Testable main function demonstrating OCR from a sample PDF path.
    """
    return extract_text_from_pdf(input_path, language)


if __name__ == "__main__":
    """
    Example usage:
      python ocr_engine.py --input path/to/input.pdf --output path/to/output.txt --language eng
    """
    parser = argparse.ArgumentParser(
        description="Extract text from scanned PDFs using Tesseract OCR"
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input PDF file or directory of PDFs'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output text file or directory (defaults to input path with .txt extension)'
    )
    parser.add_argument(
        '--language', '-l',
        default='eng',
        help='OCR language code (e.g., eng, spa)'
    )

    args = parser.parse_args()
    try:
        process_input(args.input, args.output, args.language)
        logging.info("Processing completed successfully.")
    except Exception as e:
        logging.error("Processing failed: %s", e)
        exit(1)
