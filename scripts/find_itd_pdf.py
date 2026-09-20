"""Find the PDF containing a specific Government Order number."""

from pathlib import Path

import fitz


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

TARGET = "24/2026/ITD"


def main() -> None:
    """Search all PDFs for the target Government Order."""

    for pdf_path in sorted(RAW_DATA_DIR.glob("*.pdf")):
        try:
            with fitz.open(pdf_path) as document:
                text = "\n".join(
                    page.get_text()
                    for page in document
                )

            if TARGET.lower() in text.lower():
                print(f"FOUND: {pdf_path.name}")

        except Exception as exc:
            print(
                f"ERROR: {pdf_path.name} -> {exc}"
            )


if __name__ == "__main__":
    main()