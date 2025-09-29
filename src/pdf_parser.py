"""
PDF parsing module for ADP paystub extraction.

This module handles extracting text from ADP paystub PDFs using pdfplumber,
providing structured access to paystub content with position information.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pdfplumber

logger = logging.getLogger(__name__)


class PDFParsingError(Exception):
    """Raised when there's an error parsing PDF content."""
    pass


class RawPaystubText:
    """Container for raw text extracted from paystub PDF."""

    def __init__(self, text: str, tables: List[List[List[str]]], metadata: Dict[str, str]):
        self.text = text
        self.tables = tables
        self.metadata = metadata
        self.lines = [line.strip() for line in text.split('\n') if line.strip()]

    def find_lines_containing(self, pattern: str, case_sensitive: bool = False) -> List[str]:
        """Find all lines containing the specified pattern."""
        if case_sensitive:
            return [line for line in self.lines if pattern in line]
        else:
            pattern_lower = pattern.lower()
            return [line for line in self.lines if pattern_lower in line.lower()]

    def find_line_after(self, pattern: str, offset: int = 1) -> Optional[str]:
        """Find line that appears after a line containing the pattern."""
        pattern_lower = pattern.lower()
        for i, line in enumerate(self.lines):
            if pattern_lower in line.lower():
                if i + offset < len(self.lines):
                    return self.lines[i + offset]
        return None

    def extract_between_patterns(self, start_pattern: str, end_pattern: str) -> List[str]:
        """Extract all lines between two patterns."""
        start_pattern_lower = start_pattern.lower()
        end_pattern_lower = end_pattern.lower()

        start_idx = None
        for i, line in enumerate(self.lines):
            if start_pattern_lower in line.lower():
                start_idx = i + 1
                break

        if start_idx is None:
            return []

        end_idx = len(self.lines)
        for i in range(start_idx, len(self.lines)):
            if end_pattern_lower in self.lines[i].lower():
                end_idx = i
                break

        return self.lines[start_idx:end_idx]


class PDFParser:
    """Handles PDF text extraction from ADP paystubs."""

    def __init__(self):
        """Initialize PDF parser."""
        self.supported_extensions = {'.pdf'}

    def extract_text(self, pdf_path: str) -> RawPaystubText:
        """
        Extract text content from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            RawPaystubText object containing extracted content

        Raises:
            PDFParsingError: If PDF cannot be parsed
        """
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            raise PDFParsingError(f"PDF file not found: {pdf_path}")

        if pdf_file.suffix.lower() not in self.supported_extensions:
            raise PDFParsingError(f"Unsupported file type: {pdf_file.suffix}")

        try:
            return self._extract_with_pdfplumber(pdf_file)
        except Exception as e:
            raise PDFParsingError(f"Error extracting text from {pdf_path}: {str(e)}")

    def _extract_with_pdfplumber(self, pdf_file: Path) -> RawPaystubText:
        """Extract text using pdfplumber library."""
        all_text = []
        all_tables = []
        metadata = {}

        logger.info(f"Extracting text from {pdf_file.name}")

        try:
            with pdfplumber.open(pdf_file) as pdf:
                metadata['num_pages'] = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)

                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)

                    logger.debug(f"Processed page {page_num + 1}/{len(pdf.pages)}")

        except Exception as e:
            raise PDFParsingError(f"pdfplumber extraction failed: {str(e)}")

        combined_text = '\n'.join(all_text)

        if not combined_text.strip():
            raise PDFParsingError("No text content found in PDF - may be image-based")

        logger.info(f"Successfully extracted {len(combined_text)} characters from {metadata['num_pages']} pages")

        return RawPaystubText(
            text=combined_text,
            tables=all_tables,
            metadata=metadata
        )

    def analyze_pdf_structure(self, pdf_path: str) -> Dict[str, any]:
        """
        Analyze PDF structure to understand layout and content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with structure analysis
        """
        try:
            raw_text = self.extract_text(pdf_path)

            analysis = {
                'file_name': Path(pdf_path).name,
                'num_pages': raw_text.metadata.get('num_pages', 0),
                'total_lines': len(raw_text.lines),
                'has_tables': len(raw_text.tables) > 0,
                'num_tables': len(raw_text.tables),
                'text_length': len(raw_text.text),
                'sample_lines': raw_text.lines[:10],  # First 10 lines for inspection
                'key_patterns_found': self._find_key_patterns(raw_text)
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing PDF structure: {e}")
            return {'error': str(e)}

    def _find_key_patterns(self, raw_text: RawPaystubText) -> Dict[str, bool]:
        """Find key patterns that indicate ADP paystub sections."""
        patterns = {
            'pay_date': any('pay date' in line.lower() for line in raw_text.lines),
            'earnings': any('earnings' in line.lower() for line in raw_text.lines),
            'deductions': any('deductions' in line.lower() for line in raw_text.lines),
            'net_pay': any('net pay' in line.lower() for line in raw_text.lines),
            'rsu_vest': any('rsu vest' in line.lower() for line in raw_text.lines),
            'regular_pay': any('regular' in line.lower() for line in raw_text.lines),
            'federal_tax': any('federal income tax' in line.lower() for line in raw_text.lines),
            'advice_number': any('advice' in line.lower() for line in raw_text.lines),
        }

        return patterns

    def extract_currency_amounts(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract currency amounts from text.

        Args:
            text: Text to search for currency amounts

        Returns:
            List of tuples (original_text, amount)
        """
        # Pattern to match currency amounts (with or without dollar signs, commas)
        currency_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

        matches = []
        for match in re.finditer(currency_pattern, text):
            original = match.group(0)
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                matches.append((original, amount))
            except ValueError:
                continue

        return matches

    def preview_pdf_content(self, pdf_path: str, max_lines: int = 50) -> str:
        """
        Get a preview of PDF content for debugging.

        Args:
            pdf_path: Path to PDF file
            max_lines: Maximum number of lines to return

        Returns:
            String with preview content
        """
        try:
            raw_text = self.extract_text(pdf_path)
            preview_lines = raw_text.lines[:max_lines]
            return '\n'.join(preview_lines)
        except Exception as e:
            return f"Error previewing PDF: {str(e)}"


def analyze_sample_pdf(pdf_path: str) -> None:
    """Utility function to analyze a sample PDF and print results."""
    parser = PDFParser()

    print(f"Analyzing: {pdf_path}")
    print("=" * 50)

    # Structure analysis
    analysis = parser.analyze_pdf_structure(pdf_path)

    print("PDF Structure Analysis:")
    for key, value in analysis.items():
        if key == 'sample_lines':
            print(f"{key}: (showing first 10 lines)")
            for i, line in enumerate(value, 1):
                print(f"  {i:2d}: {line}")
        else:
            print(f"{key}: {value}")

    print("\n" + "=" * 50)
    print("Content Preview (first 30 lines):")
    print(parser.preview_pdf_content(pdf_path, 30))


if __name__ == "__main__":
    # Test with sample PDF
    import sys

    sample_pdfs = [
        "data/Pay Date 2025-08-29.pdf",  # Regular paystub
        "data/Pay Date 2025-08-22.pdf",  # RSU vesting
        "data/Pay Date 2025-09-30.pdf"   # Another regular paystub
    ]

    parser = PDFParser()

    for pdf_path in sample_pdfs:
        if Path(pdf_path).exists():
            print(f"\n{'='*60}")
            analyze_sample_pdf(pdf_path)
        else:
            print(f"PDF not found: {pdf_path}")