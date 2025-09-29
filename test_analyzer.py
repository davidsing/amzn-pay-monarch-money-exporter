#!/usr/bin/env python3
"""Test script for paystub analyzer."""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pdf_parser import PDFParser
from src.paystub_analyzer import PaystubAnalyzer
from src.config_manager import ConfigManager

def test_paystub_analysis():
    """Test paystub analysis with sample PDFs."""

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    sample_pdfs = [
        "data/Pay Date 2025-08-29.pdf",  # Regular paystub
        "data/Pay Date 2025-08-22.pdf",  # RSU vesting
        "data/Pay Date 2025-09-30.pdf"   # Another regular paystub
    ]

    parser = PDFParser()
    analyzer = PaystubAnalyzer()

    for pdf_path in sample_pdfs:
        if Path(pdf_path).exists():
            print(f"\n{'='*60}")
            print(f"Analyzing: {pdf_path}")
            print("=" * 60)

            try:
                raw_text = parser.extract_text(pdf_path)
                paystub_data = analyzer.analyze_paystub(raw_text, pdf_path)

                print(f"Pay Date: {paystub_data.pay_date.strftime('%Y-%m-%d')}")
                print(f"RSU Vest Event: {paystub_data.is_rsu_vest}")
                print(f"Gross Pay: ${paystub_data.gross_pay:,.2f}")
                print(f"Net Pay: ${paystub_data.net_pay:,.2f}")
                print(f"Total Deductions: ${paystub_data.calculate_total_deductions():,.2f}")
                print(f"Balance Valid: {paystub_data.validate_balance()}")

                print(f"\nEarnings ({len(paystub_data.earnings)} items):")
                for earning in paystub_data.earnings:
                    print(f"  {earning.description}: ${earning.amount:,.2f} ({earning.category})")

                print(f"\nDeductions ({len(paystub_data.deductions)} items):")
                for deduction in paystub_data.deductions:
                    print(f"  {deduction.description}: ${deduction.amount:,.2f} ({deduction.category})")

                print(f"\nDistributions ({len(paystub_data.distributions)} items):")
                for dist in paystub_data.distributions:
                    print(f"  {dist.description}: ${dist.amount:,.2f} ({dist.account})")

            except Exception as e:
                print(f"Error analyzing {pdf_path}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"PDF not found: {pdf_path}")

if __name__ == "__main__":
    test_paystub_analysis()