"""
CSV generation module for Monarch Money compatible output.

This module converts PaystubData into properly formatted CSV files
that can be imported into Monarch Money.
"""

import csv
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional

try:
    from .paystub_analyzer import PaystubData, Transaction
    from .config_manager import ConfigManager
except ImportError:
    # For standalone testing
    from paystub_analyzer import PaystubData, Transaction
    from config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CSVGenerationError(Exception):
    """Raised when there's an error generating CSV output."""
    pass


class MonarchCSVGenerator:
    """Generates Monarch Money compatible CSV files from paystub data."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize CSV generator with configuration."""
        self.config = config_manager or ConfigManager()
        self.config.load_settings()
        self.config.load_category_mappings()

        # Monarch Money CSV format specification
        self.column_headers = self.config.get_setting(
            'monarch_money.column_order',
            ["date", "description", "original_description", "amount",
             "transaction_type", "category", "account_name", "labels", "notes"]
        )

    def generate_csv(self, paystub_data: PaystubData, output_path: str) -> str:
        """
        Generate CSV file from paystub data.

        Args:
            paystub_data: Analyzed paystub data
            output_path: Path for output CSV file

        Returns:
            Path to generated CSV file

        Raises:
            CSVGenerationError: If CSV generation fails
        """
        try:
            logger.info(f"Generating CSV for paystub dated {paystub_data.pay_date.strftime('%Y-%m-%d')}")

            # Convert paystub data to CSV rows
            csv_rows = self._convert_to_csv_rows(paystub_data)

            # Write CSV file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.column_headers)

                # Write header
                writer.writeheader()

                # Write data rows
                for row in csv_rows:
                    writer.writerow(row)

            logger.info(f"Generated CSV with {len(csv_rows)} transactions: {output_file}")
            return str(output_file)

        except Exception as e:
            raise CSVGenerationError(f"Error generating CSV: {str(e)}")

    def _convert_to_csv_rows(self, paystub_data: PaystubData) -> List[Dict[str, str]]:
        """Convert paystub data to CSV row dictionaries."""
        rows = []

        # Add earnings (income) transactions
        for earning in paystub_data.earnings:
            row = self._create_csv_row(
                date=paystub_data.pay_date,
                description=earning.description,
                amount=earning.amount,
                transaction_type="credit",
                category=earning.category,
                account_name=self._get_primary_account(),
                paystub_data=paystub_data,
                transaction=earning
            )
            rows.append(row)

        # Add deduction transactions (expenses)
        for deduction in paystub_data.deductions:
            row = self._create_csv_row(
                date=paystub_data.pay_date,
                description=deduction.description,
                amount=-abs(deduction.amount),  # Negative for expenses
                transaction_type="debit",
                category=deduction.category,
                account_name=self._get_primary_account(),
                paystub_data=paystub_data,
                transaction=deduction
            )
            rows.append(row)

        # Add net pay distributions (transfers)
        for distribution in paystub_data.distributions:
            row = self._create_csv_row(
                date=paystub_data.pay_date,
                description=distribution.description,
                amount=distribution.amount,
                transaction_type="credit",
                category="Transfer:Direct Deposit",
                account_name=distribution.account or self._get_primary_account(),
                paystub_data=paystub_data,
                transaction=distribution
            )
            rows.append(row)

        return rows

    def _create_csv_row(self, date: datetime, description: str, amount: Decimal,
                       transaction_type: str, category: str, account_name: str,
                       paystub_data: PaystubData, transaction: Transaction) -> Dict[str, str]:
        """Create a CSV row dictionary in Monarch Money format."""

        # Format amount with proper precision
        amount_precision = self.config.get_setting('monarch_money.amount_precision', 2)
        formatted_amount = f"{amount:.{amount_precision}f}"

        # Create notes with additional context
        notes = self._generate_notes(paystub_data, transaction)

        # Create the row according to Monarch Money format
        row = {
            "date": date.strftime('%Y-%m-%d'),
            "description": description,
            "original_description": transaction.original_text[:100] if transaction.original_text else "",
            "amount": formatted_amount,
            "transaction_type": transaction_type,
            "category": category,
            "account_name": account_name,
            "labels": self._generate_labels(paystub_data),
            "notes": notes
        }

        return row

    def _generate_notes(self, paystub_data: PaystubData, transaction: Transaction) -> str:
        """Generate notes for the transaction."""
        notes_parts = []

        # Add pay period information
        notes_parts.append(f"Pay Date: {paystub_data.pay_date.strftime('%Y-%m-%d')}")

        # Add period information if different from pay date
        if paystub_data.period_start != paystub_data.pay_date:
            period_str = f"{paystub_data.period_start.strftime('%Y-%m-%d')} to {paystub_data.period_end.strftime('%Y-%m-%d')}"
            notes_parts.append(f"Period: {period_str}")

        # Add RSU event indicator
        if paystub_data.is_rsu_vest:
            notes_parts.append("RSU Vesting Event")

        # Add advice number for tracking
        notes_parts.append(f"Advice: {paystub_data.advice_number}")

        return " | ".join(notes_parts)

    def _generate_labels(self, paystub_data: PaystubData) -> str:
        """Generate labels for categorization."""
        labels = []

        if paystub_data.is_rsu_vest:
            labels.append("RSU")

        labels.append("Payroll")
        labels.append(f"Pay-{paystub_data.pay_date.strftime('%Y-%m')}")

        return ",".join(labels)

    def _get_primary_account(self) -> str:
        """Get the primary account name for transactions."""
        account_mappings = self.config.category_mappings.get('account_mappings', {})
        return account_mappings.get('checking_acct_1', 'Primary Checking')

    def generate_batch_csv(self, paystub_data_list: List[PaystubData], output_dir: str) -> List[str]:
        """
        Generate CSV files for multiple paystubs.

        Args:
            paystub_data_list: List of analyzed paystub data
            output_dir: Directory for output CSV files

        Returns:
            List of paths to generated CSV files
        """
        generated_files = []
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        for paystub_data in paystub_data_list:
            # Generate filename based on pay date and advice number
            filename = f"{paystub_data.pay_date.strftime('%Y-%m-%d')}_{paystub_data.advice_number}_monarch.csv"
            output_path = output_directory / filename

            try:
                generated_file = self.generate_csv(paystub_data, str(output_path))
                generated_files.append(generated_file)
            except CSVGenerationError as e:
                logger.error(f"Failed to generate CSV for {paystub_data.pay_date}: {e}")

        logger.info(f"Generated {len(generated_files)} CSV files in {output_dir}")
        return generated_files

    def validate_csv_format(self, csv_path: str) -> bool:
        """
        Validate that generated CSV meets Monarch Money requirements.

        Args:
            csv_path: Path to CSV file to validate

        Returns:
            True if CSV format is valid
        """
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Check headers
                if reader.fieldnames != self.column_headers:
                    logger.error(f"Invalid headers in {csv_path}: {reader.fieldnames}")
                    return False

                # Validate each row
                row_count = 0
                for row in reader:
                    row_count += 1

                    # Check required fields
                    if not all(field in row for field in self.column_headers):
                        logger.error(f"Missing fields in row {row_count}")
                        return False

                    # Validate date format
                    try:
                        datetime.strptime(row['date'], '%Y-%m-%d')
                    except ValueError:
                        logger.error(f"Invalid date format in row {row_count}: {row['date']}")
                        return False

                    # Validate amount format
                    try:
                        float(row['amount'])
                    except ValueError:
                        logger.error(f"Invalid amount format in row {row_count}: {row['amount']}")
                        return False

                    # Validate transaction type
                    if row['transaction_type'] not in ['credit', 'debit']:
                        logger.error(f"Invalid transaction type in row {row_count}: {row['transaction_type']}")
                        return False

                logger.info(f"CSV validation passed: {csv_path} ({row_count} rows)")
                return True

        except Exception as e:
            logger.error(f"Error validating CSV {csv_path}: {e}")
            return False

    def preview_csv_output(self, paystub_data: PaystubData, max_rows: int = 10) -> str:
        """
        Generate a preview of CSV output without writing to file.

        Args:
            paystub_data: Paystub data to preview
            max_rows: Maximum number of rows to show

        Returns:
            String representation of CSV content
        """
        rows = self._convert_to_csv_rows(paystub_data)

        # Create CSV content as string
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.column_headers)
        writer.writeheader()

        for i, row in enumerate(rows[:max_rows]):
            writer.writerow(row)

        if len(rows) > max_rows:
            output.write(f"... and {len(rows) - max_rows} more rows\n")

        return output.getvalue()


def generate_sample_csv(pdf_path: str, output_path: str) -> str:
    """Utility function to generate CSV from a single PDF."""
    try:
        from .pdf_parser import PDFParser
        from .paystub_analyzer import PaystubAnalyzer
    except ImportError:
        from pdf_parser import PDFParser
        from paystub_analyzer import PaystubAnalyzer

    # Parse and analyze paystub
    parser = PDFParser()
    analyzer = PaystubAnalyzer()
    raw_text = parser.extract_text(pdf_path)
    paystub_data = analyzer.analyze_paystub(raw_text, pdf_path)

    # Generate CSV
    generator = MonarchCSVGenerator()
    return generator.generate_csv(paystub_data, output_path)


if __name__ == "__main__":
    # Test CSV generation with sample PDFs
    from pathlib import Path

    sample_pdfs = [
        "data/Pay Date 2025-08-29.pdf",
        "data/Pay Date 2025-08-22.pdf",
        "data/Pay Date 2025-09-30.pdf"
    ]

    generator = MonarchCSVGenerator()

    for pdf_path in sample_pdfs:
        if Path(pdf_path).exists():
            print(f"\n{'='*60}")
            print(f"Generating CSV for: {pdf_path}")
            print("=" * 60)

            try:
                # Generate output filename
                pdf_name = Path(pdf_path).stem
                output_path = f"output/{pdf_name}_monarch.csv"

                # Generate CSV
                csv_path = generate_sample_csv(pdf_path, output_path)
                print(f"Generated: {csv_path}")

                # Validate the CSV
                is_valid = generator.validate_csv_format(csv_path)
                print(f"Validation: {'PASSED' if is_valid else 'FAILED'}")

                # Show preview
                try:
                    from pdf_parser import PDFParser
                    from paystub_analyzer import PaystubAnalyzer

                    parser = PDFParser()
                    analyzer = PaystubAnalyzer()
                    raw_text = parser.extract_text(pdf_path)
                    paystub_data = analyzer.analyze_paystub(raw_text, pdf_path)

                    print("\nCSV Preview:")
                    print(generator.preview_csv_output(paystub_data, max_rows=5))

                except Exception as e:
                    print(f"Error generating preview: {e}")

            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"PDF not found: {pdf_path}")