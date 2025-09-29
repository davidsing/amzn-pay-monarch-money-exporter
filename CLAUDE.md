# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **ADP Paystub to Monarch Money CSV Exporter** - a Python project that extracts data from ADP paystub PDF files and generates CSV files compatible with Monarch Money import. The tool provides detailed gross pay breakdowns showing constituent components for better financial tracking.

## Project Structure

The project follows this planned structure (as outlined in IMPLEMENTATION_PLAN.md):

```
amzn-pay-exporter/
├── src/                        # Main source code (to be created)
│   ├── main.py                 # CLI entry point
│   ├── pdf_parser.py           # PDF text extraction using pdfplumber
│   ├── paystub_analyzer.py     # Parse ADP paystub structure
│   ├── csv_generator.py        # Generate Monarch Money CSV
│   ├── config_manager.py       # Load and validate configuration
│   └── validators.py           # Data validation utilities
├── config/                     # Configuration files
│   ├── category_mappings.json  # Transaction categorization rules
│   └── settings.json          # General script configuration
├── data/                       # Input PDF files (sample paystubs)
├── output/                     # Generated CSV files (to be created)
├── logs/                       # Processing logs (to be created)
└── tests/                      # Unit tests (to be created)
```

## Key Architecture Components

### Configuration System
- **settings.json**: Monarch Money CSV format settings, processing options, file handling, validation rules
- **category_mappings.json**: Maps ADP paystub components to Monarch Money categories
  - Earnings: Regular pay, RSU vesting, PTO, holiday pay
  - Deductions: Statutory taxes, retirement (401k), healthcare (HSA, insurance), life insurance
  - Special RSU handling with different tax categorization

### Data Processing Flow
1. **PDF Parsing**: Extract text from ADP PDFs using pdfplumber
2. **Paystub Analysis**: Parse earnings, deductions, net pay distributions
3. **Transaction Generation**: Convert to Monarch Money 9-column CSV format
4. **Validation**: Verify gross pay = net pay + total deductions

### Monarch Money CSV Format
- **9 columns**: Date, Description, Original Description, Amount, Transaction Type, Category, Account Name, Labels, Notes
- **Transaction Types**: "credit" for income, "debit" for deductions
- **Amount Format**: Positive for income, negative for expenses (dash format)
- **Date Format**: YYYY-MM-DD

## Development Commands

Since this is a Python project in early development phase, typical commands would be:

```bash
# Set up development environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt  # when created

# Run the main script
python src/main.py

# Run tests
python -m pytest tests/  # when tests are created

# Lint code (when configured)
flake8 src/
black src/

# Type checking (when configured)
mypy src/
```

## Special Considerations

### RSU vs Regular Pay Processing
- **RSU Detection**: Special logic needed to identify RSU vesting events vs regular paystubs
- **Tax Handling**: RSU vesting has heavy tax withholding requiring different categorization
- **Categories**: Stock compensation uses "Income:Stock Compensation" vs "Income:Salary"

### Data Validation Requirements
- Gross pay must equal net pay + total deductions
- All transactions require advice number for deduplication
- Support for multiple deposit accounts (checking, savings)

### PDF Processing
- Uses pdfplumber library for text extraction
- Handles multi-page PDFs
- Flexible parsing patterns to accommodate ADP format variations

## Current State
This project is in the planning/setup phase. The main implementation files (src/ directory) have not yet been created. The configuration files are ready and contain detailed category mappings for ADP paystub components.

## Sample Data
- Input PDFs in `data/`: Contains sample ADP paystubs (regular pay and RSU vesting)
- Reference materials in `reference/`: Monarch Money CSV format examples