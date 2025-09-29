# ADP Paystub to Monarch Money CSV Exporter

A Python tool that extracts data from ADP paystub PDF files and generates CSV files compatible with Monarch Money import. This tool provides detailed gross pay breakdowns showing constituent components for better financial tracking.

## Features

- **PDF Processing**: Extracts text from ADP paystub PDFs using advanced parsing
- **Smart Categorization**: Automatically categorizes earnings and deductions
- **RSU Support**: Special handling for RSU vesting events vs regular paystubs
- **Monarch Money Integration**: Generates properly formatted 9-column CSV files
- **Validation**: Ensures gross pay = net pay + total deductions
- **Batch Processing**: Process multiple PDFs at once
- **Configurable**: JSON-based configuration for categories and settings

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/davidsing/amzn-pay-monarch-money-exporter.git
cd amzn-pay-monarch-money-exporter
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Basic Usage

Process a single paystub:
```bash
python src/main.py data/Pay\ Date\ 2025-08-29.pdf
```

Process all paystubs in a directory:
```bash
python src/main.py data/
```

## Project Structure

```
amzn-pay-exporter/
├── src/                        # Main source code
│   ├── main.py                 # CLI entry point
│   ├── pdf_parser.py           # PDF text extraction
│   ├── paystub_analyzer.py     # Parse ADP paystub structure
│   ├── csv_generator.py        # Generate Monarch Money CSV
│   ├── config_manager.py       # Configuration management
│   └── validators.py           # Data validation utilities
├── config/                     # Configuration files
│   ├── category_mappings.json  # Transaction categorization rules
│   └── settings.json          # General settings
├── data/                       # Sample input PDF files
├── output/                     # Generated CSV files
├── tests/                      # Unit tests
└── logs/                       # Processing logs
```

## Configuration

### Category Mappings (`config/category_mappings.json`)

Maps ADP paystub components to Monarch Money categories:

- **Earnings**: Regular pay, RSU vesting, PTO, holiday pay
- **Deductions**: Taxes, retirement (401k), healthcare (HSA, insurance), life insurance
- **Special RSU Handling**: Different categorization for stock compensation

### Settings (`config/settings.json`)

Controls processing behavior:

- **Monarch Money Format**: 9-column CSV specification
- **File Handling**: Input/output directories, naming conventions
- **Validation**: Balance checking, duplicate detection
- **Logging**: Log levels and output configuration

## Supported Paystub Types

### Regular Paystubs
- Monthly salary payments
- Standard deductions (taxes, benefits, insurance)
- Multiple deposit accounts

### RSU Vesting Events
- Stock vesting income
- Heavy tax withholding
- Special categorization for stock compensation

## Output Format

Generates Monarch Money compatible CSV with 9 columns:
1. Date (YYYY-MM-DD)
2. Description
3. Original Description
4. Amount (positive for income, negative for expenses)
5. Transaction Type (credit/debit)
6. Category
7. Account Name
8. Labels
9. Notes

## Example Output

```csv
Date,Description,Original Description,Amount,Transaction Type,Category,Account Name,Labels,Notes
2025-08-29,Regular salary income,,5000.00,credit,Income:Salary,Primary Checking,,Pay Date: 2025-08-29
2025-08-29,Federal income tax withholding,,-1200.00,debit,Taxes:Federal Income Tax,Primary Checking,,Pay Date: 2025-08-29
2025-08-29,401k traditional contribution,,-500.00,debit,Transfer:401k Traditional,Primary Checking,,Pay Date: 2025-08-29
```

## Data Validation

The tool automatically validates:
- Gross pay equals net pay plus total deductions
- All required fields are present
- Reasonable amount ranges
- Duplicate detection using advice numbers

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_config_manager.py
```

### Adding New Categories

1. Update `config/category_mappings.json` with new categories
2. Add corresponding patterns in `field_mappings` section
3. Test with sample paystubs

## Troubleshooting

### Common Issues

1. **PDF parsing errors**: Ensure PDFs are text-based, not scanned images
2. **Balance validation failures**: Check for missing or misclassified transactions
3. **Category mapping issues**: Verify patterns in `category_mappings.json` match PDF text

### Logging

Logs are written to `logs/paystub_processor.log` and console. Adjust log level in `config/settings.json`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review log files for detailed error information