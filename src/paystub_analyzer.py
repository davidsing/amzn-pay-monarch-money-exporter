"""
Paystub analysis module for extracting structured data from ADP paystubs.

This module analyzes the raw text extracted from PDFs and converts it into
structured data including earnings, deductions, and metadata.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple

try:
    from .pdf_parser import RawPaystubText
    from .config_manager import ConfigManager
except ImportError:
    # For standalone testing
    from pdf_parser import RawPaystubText
    from config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Represents a single financial transaction from the paystub."""
    description: str
    amount: Decimal
    category: str = ""
    account: str = ""
    notes: str = ""
    original_text: str = ""

    def __post_init__(self):
        """Ensure amount is a Decimal."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


@dataclass
class PaystubData:
    """Structured data extracted from a paystub."""
    pay_date: datetime
    period_start: datetime
    period_end: datetime
    advice_number: str
    gross_pay: Decimal
    net_pay: Decimal
    earnings: List[Transaction] = field(default_factory=list)
    deductions: List[Transaction] = field(default_factory=list)
    distributions: List[Transaction] = field(default_factory=list)
    is_rsu_vest: bool = False
    raw_text_preview: str = ""

    def __post_init__(self):
        """Ensure monetary values are Decimals."""
        for attr in ['gross_pay', 'net_pay']:
            value = getattr(self, attr)
            if not isinstance(value, Decimal):
                setattr(self, attr, Decimal(str(value)))

    def calculate_total_deductions(self) -> Decimal:
        """Calculate total deductions amount."""
        return sum(txn.amount for txn in self.deductions)

    def validate_balance(self) -> bool:
        """Validate that gross pay equals net pay plus deductions."""
        total_deductions = self.calculate_total_deductions()
        expected_net = self.gross_pay - total_deductions
        # Allow for small rounding differences
        return abs(expected_net - self.net_pay) < Decimal('0.01')


class PaystubAnalysisError(Exception):
    """Raised when there's an error analyzing paystub content."""
    pass


class PaystubAnalyzer:
    """Analyzes raw paystub text and extracts structured data."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize analyzer with configuration."""
        self.config = config_manager or ConfigManager()
        self.config.load_settings()
        self.config.load_category_mappings()

    def analyze_paystub(self, raw_text: RawPaystubText, pdf_filename: str = "") -> PaystubData:
        """
        Analyze raw paystub text and extract structured data.

        Args:
            raw_text: Raw text extracted from PDF
            pdf_filename: Original PDF filename for context

        Returns:
            PaystubData with extracted information

        Raises:
            PaystubAnalysisError: If analysis fails
        """
        try:
            logger.info(f"Analyzing paystub: {pdf_filename}")

            # Extract metadata first
            metadata = self._extract_metadata(raw_text)

            # Determine if this is an RSU vesting event
            is_rsu_vest = self._detect_rsu_vesting(raw_text)

            # Extract financial data
            earnings = self._extract_earnings(raw_text, is_rsu_vest)
            deductions = self._extract_deductions(raw_text, is_rsu_vest)
            distributions = self._extract_distributions(raw_text)

            # Calculate totals
            gross_pay = sum(txn.amount for txn in earnings)
            net_pay = sum(txn.amount for txn in distributions)

            paystub_data = PaystubData(
                pay_date=metadata['pay_date'],
                period_start=metadata['period_start'],
                period_end=metadata['period_end'],
                advice_number=metadata['advice_number'],
                gross_pay=gross_pay,
                net_pay=net_pay,
                earnings=earnings,
                deductions=deductions,
                distributions=distributions,
                is_rsu_vest=is_rsu_vest,
                raw_text_preview='\n'.join(raw_text.lines[:20])
            )

            # Validate the data
            if not paystub_data.validate_balance():
                logger.warning(f"Balance validation failed for {pdf_filename}")
                logger.warning(f"Gross: {gross_pay}, Net: {net_pay}, Deductions: {paystub_data.calculate_total_deductions()}")

            logger.info(f"Successfully analyzed paystub: {pdf_filename}")
            logger.info(f"RSU Vest: {is_rsu_vest}, Gross: {gross_pay}, Net: {net_pay}")

            return paystub_data

        except Exception as e:
            raise PaystubAnalysisError(f"Error analyzing paystub {pdf_filename}: {str(e)}")

    def _extract_metadata(self, raw_text: RawPaystubText) -> Dict[str, any]:
        """Extract metadata like dates and advice number."""
        metadata = {}

        # Extract pay date
        pay_date_line = raw_text.find_line_after("Pay Date:")
        if pay_date_line:
            pay_date_match = re.search(r'Pay Date:\s*(\d{2}/\d{2}/\d{4})', ' '.join(raw_text.lines))
            if pay_date_match:
                metadata['pay_date'] = datetime.strptime(pay_date_match.group(1), '%m/%d/%Y')
            else:
                raise PaystubAnalysisError("Could not parse pay date")
        else:
            raise PaystubAnalysisError("Pay date not found")

        # Extract period dates
        period_start_match = re.search(r'Period Beginning:\s*(\d{2}/\d{2}/\d{4})', ' '.join(raw_text.lines))
        period_end_match = re.search(r'Period Ending:\s*(\d{2}/\d{2}/\d{4})', ' '.join(raw_text.lines))

        if period_start_match:
            metadata['period_start'] = datetime.strptime(period_start_match.group(1), '%m/%d/%Y')
        else:
            # Default to first day of pay month
            metadata['period_start'] = metadata['pay_date'].replace(day=1)

        if period_end_match:
            metadata['period_end'] = datetime.strptime(period_end_match.group(1), '%m/%d/%Y')
        else:
            # Default to pay date
            metadata['period_end'] = metadata['pay_date']

        # Extract advice number (appears in encoded sections, extract from filename or use pay date)
        advice_number = f"ADV_{metadata['pay_date'].strftime('%Y%m%d')}"
        metadata['advice_number'] = advice_number

        return metadata

    def _detect_rsu_vesting(self, raw_text: RawPaystubText) -> bool:
        """Detect if this paystub represents an RSU vesting event."""
        # Look for RSU Vest in earnings
        rsu_lines = raw_text.find_lines_containing("rsu vest", case_sensitive=False)
        if not rsu_lines:
            return False

        # Extract RSU vest amount and compare to other earnings
        rsu_amount = self._extract_amounts_from_lines(rsu_lines)
        regular_lines = raw_text.find_lines_containing("regular", case_sensitive=False)
        regular_amount = self._extract_amounts_from_lines(regular_lines)

        # If RSU vest amount is significantly large or if regular pay is minimal, it's likely RSU focused
        if rsu_amount and regular_amount:
            return rsu_amount[0] > regular_amount[0] * 2  # RSU is more than 2x regular pay
        elif rsu_amount:
            return rsu_amount[0] > 10000  # Large RSU amount (>$10k)

        return len(rsu_lines) > 0

    def _extract_earnings(self, raw_text: RawPaystubText, is_rsu_vest: bool) -> List[Transaction]:
        """Extract earnings transactions."""
        earnings = []

        # Common earnings patterns to look for
        earnings_patterns = {
            'regular': ['Regular'],
            'rsu_vest': ['Rsu Vest', 'RSU Vest'],
            'flex_pto': ['Flex/Pto', 'Flex/PTO'],
            'holiday_pay': ['Holiday Pay'],
            'std_pto_pay': ['Stnd Pto Pay', 'Std Pto Pay'],
            'imputed_income': ['Imputed Income']
        }

        for earning_type, patterns in earnings_patterns.items():
            for pattern in patterns:
                matching_lines = raw_text.find_lines_containing(pattern)
                for line in matching_lines:
                    amounts = self._extract_amounts_from_line(line)
                    if amounts:
                        # Take the first significant amount (usually the current period)
                        amount = max(amounts)  # Use the largest amount found in the line
                        if amount > 0:
                            category_mapping = self.config.get_category_mapping('earnings', earning_type)
                            category = category_mapping['category'] if category_mapping else f"Income:{earning_type.title()}"
                            description = category_mapping['description'] if category_mapping else pattern

                            earnings.append(Transaction(
                                description=description,
                                amount=Decimal(str(amount)),
                                category=category,
                                original_text=line
                            ))
                            break  # Only take the first match for each pattern

        return earnings

    def _extract_deductions(self, raw_text: RawPaystubText, is_rsu_vest: bool) -> List[Transaction]:
        """Extract deduction transactions."""
        deductions = []

        # Look for deductions section - usually after "Statutory" or similar
        deduction_patterns = {
            'federal_income_tax': ['Federal Income Tax'],
            'medicare_tax': ['Medicare Tax'],
            'medicare_surtax': ['Medicare Surtax'],
            'social_security_tax': ['Social Security Tax'],
            'wa_paid_family_leave': ['WA Paid Family Leave'],
            'wa_paid_medical_leave': ['WA Paid Medical Leave'],
            '401k_traditional': ['401K-Trad'],
            '401k_after_tax': ['401K After Tax'],
            'hsa': ['Hsa', 'HSA'],
            'pre_tax_medical': ['Pre-Tax Medical'],
            'pre_tax_dental': ['Pre-Tax Dental'],
            'pre_tax_vision': ['Pre-Tax Vision'],
            'groupterm_life': ['Groupterm Life'],
            'supp_life_ins': ['Supp Life Ins'],
            'supp_add': ['Supp Ad/D'],
            'critic_illness': ['Critic Illness'],
            'oc_park_charge': ['Oc Park Charge'],
        }

        for deduction_type, patterns in deduction_patterns.items():
            for pattern in patterns:
                matching_lines = raw_text.find_lines_containing(pattern)
                for line in matching_lines:
                    amounts = self._extract_amounts_from_line(line)
                    if amounts:
                        # For deductions, look for negative amounts or amounts after the description
                        amount = max(amounts)  # Take the largest amount (current period)
                        if amount > 0:
                            # Get category mapping
                            category_mapping = None
                            for section in ['statutory', 'retirement', 'healthcare', 'life_insurance', 'other']:
                                cat_map = self.config.get_category_mapping(f'deductions.{section}', deduction_type)
                                if cat_map:
                                    category_mapping = cat_map
                                    break

                            if not category_mapping:
                                category = f"Deductions:{deduction_type.title()}"
                                description = pattern
                            else:
                                category = category_mapping['category']
                                description = category_mapping['description']

                            deductions.append(Transaction(
                                description=description,
                                amount=Decimal(str(amount)),
                                category=category,
                                original_text=line
                            ))
                            break

        return deductions

    def _extract_distributions(self, raw_text: RawPaystubText) -> List[Transaction]:
        """Extract net pay distributions (bank deposits)."""
        distributions = []

        # Look for account distributions
        distribution_patterns = [
            'Checking Acct 1',
            'Checking Acct 2',
            'Savings Acct 1',
            'Net Check'
        ]

        for pattern in distribution_patterns:
            matching_lines = raw_text.find_lines_containing(pattern)
            for line in matching_lines:
                amounts = self._extract_amounts_from_line(line)
                if amounts:
                    amount = max(amounts)
                    if amount > 0:
                        account_mappings = self.config.category_mappings.get('account_mappings', {})
                        account_key = pattern.lower().replace(' ', '_')
                        account_name = account_mappings.get(account_key, pattern)

                        distributions.append(Transaction(
                            description=f"Direct deposit to {account_name}",
                            amount=Decimal(str(amount)),
                            category="Transfer:Direct Deposit",
                            account=account_name,
                            original_text=line
                        ))

        return distributions

    def _extract_amounts_from_line(self, line: str) -> List[float]:
        """Extract monetary amounts from a single line."""
        # Pattern to match currency amounts including negative values
        patterns = [
            r'-?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56 or 1234.56
            r'-(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Negative amounts
        ]

        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                try:
                    # Remove commas and convert to float
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    if amount > 0.01:  # Only include significant amounts
                        amounts.append(amount)
                except ValueError:
                    continue

        return amounts

    def _extract_amounts_from_lines(self, lines: List[str]) -> List[float]:
        """Extract monetary amounts from multiple lines."""
        all_amounts = []
        for line in lines:
            amounts = self._extract_amounts_from_line(line)
            all_amounts.extend(amounts)
        return all_amounts


def analyze_sample_paystub(pdf_path: str) -> PaystubData:
    """Utility function to analyze a sample paystub."""
    try:
        from .pdf_parser import PDFParser
    except ImportError:
        from pdf_parser import PDFParser

    parser = PDFParser()
    analyzer = PaystubAnalyzer()

    raw_text = parser.extract_text(pdf_path)
    return analyzer.analyze_paystub(raw_text, pdf_path)


if __name__ == "__main__":
    # Test with sample PDFs
    from pathlib import Path

    sample_pdfs = [
        "data/Pay Date 2025-08-29.pdf",  # Regular paystub
        "data/Pay Date 2025-08-22.pdf",  # RSU vesting
        "data/Pay Date 2025-09-30.pdf"   # Another regular paystub
    ]

    for pdf_path in sample_pdfs:
        if Path(pdf_path).exists():
            print(f"\n{'='*60}")
            print(f"Analyzing: {pdf_path}")
            print("=" * 60)

            try:
                paystub_data = analyze_sample_paystub(pdf_path)

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
        else:
            print(f"PDF not found: {pdf_path}")