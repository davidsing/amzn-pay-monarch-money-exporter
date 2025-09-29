#!/usr/bin/env python3
"""Test script for CSV generator."""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pdf_parser import PDFParser
from src.paystub_analyzer import PaystubAnalyzer
from src.csv_generator import MonarchCSVGenerator

def test_csv_generation():
    """Test CSV generation with sample PDFs."""

    # Ensure output directory exists
    Path("output").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    sample_pdfs = [
        "data/Pay Date 2025-08-29.pdf",  # Regular paystub
        "data/Pay Date 2025-08-22.pdf",  # RSU vesting
        "data/Pay Date 2025-09-30.pdf"   # Another regular paystub
    ]

    parser = PDFParser()
    analyzer = PaystubAnalyzer()
    generator = MonarchCSVGenerator()

    for pdf_path in sample_pdfs:
        if Path(pdf_path).exists():
            print(f"\n{'='*60}")
            print(f"Processing: {pdf_path}")
            print("=" * 60)

            try:
                # Parse and analyze
                raw_text = parser.extract_text(pdf_path)
                paystub_data = analyzer.analyze_paystub(raw_text, pdf_path)

                # Generate output filename
                pdf_name = Path(pdf_path).stem.replace(" ", "_")
                output_path = f"output/{pdf_name}_monarch.csv"

                # Generate CSV
                csv_path = generator.generate_csv(paystub_data, output_path)
                print(f"✅ Generated: {csv_path}")

                # Validate the CSV
                is_valid = generator.validate_csv_format(csv_path)
                print(f"✅ Validation: {'PASSED' if is_valid else 'FAILED'}")

                # Show preview
                print("\n📄 CSV Preview (first 5 rows):")
                preview = generator.preview_csv_output(paystub_data, max_rows=5)
                print(preview)

                # Show file info
                csv_file = Path(csv_path)
                if csv_file.exists():
                    file_size = csv_file.stat().st_size
                    with open(csv_path, 'r') as f:
                        line_count = sum(1 for _ in f)
                    print(f"📊 File stats: {file_size} bytes, {line_count} lines")

            except Exception as e:
                print(f"❌ Error processing {pdf_path}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ PDF not found: {pdf_path}")

    # Test batch processing
    print(f"\n{'='*60}")
    print("Testing Batch Processing")
    print("=" * 60)

    try:
        # Collect all paystub data
        all_paystub_data = []
        for pdf_path in sample_pdfs:
            if Path(pdf_path).exists():
                raw_text = parser.extract_text(pdf_path)
                paystub_data = analyzer.analyze_paystub(raw_text, pdf_path)
                all_paystub_data.append(paystub_data)

        # Generate batch CSV files
        batch_files = generator.generate_batch_csv(all_paystub_data, "output/batch")
        print(f"✅ Generated {len(batch_files)} batch CSV files")
        for file_path in batch_files:
            print(f"   📄 {file_path}")

    except Exception as e:
        print(f"❌ Error in batch processing: {e}")

if __name__ == "__main__":
    test_csv_generation()