# ADP Paystub to Monarch Money CSV Exporter - Requirements

## Overview
A script to extract data from ADP paystub PDF files and generate CSV files compatible with Monarch Money import. The goal is to provide detailed gross pay breakdowns showing constituent components for better financial tracking.

## Input Data Analysis
Based on sample files in `/data/`:
- **Regular Pay Stubs**: 2025-08-29, 2025-09-30 (monthly salary payments)
- **RSU Vest Stub**: 2025-08-22 (stock vesting event)

### Key Data Points Identified

#### Earnings Components
- **Regular**: Base salary earnings
- **RSU Vest**: Stock vesting income (appears only on vest dates)
- **Flex/PTO**: Flexible/vacation time earnings
- **Holiday Pay**: Holiday compensation
- **Imputed Income**: Various imputed benefits
- **Std PTO Pay**: Standard PTO payout

#### Deductions Categories
**Statutory (Pre-tax)**:
- Federal Income Tax
- Medicare Tax/Surtax
- Social Security Tax
- WA Paid Family/Medical Leave

**Benefits (Pre-tax)**:
- 401K Traditional & After-tax contributions
- HSA contributions
- Pre-tax Medical/Dental/Vision insurance
- Life insurance premiums (multiple types)
- Critical illness, AD&D insurance

**Other Deductions**:
- Parking charges
- Various insurance premiums

#### Net Pay Distribution
- Multiple checking/savings account deposits
- Net check amount (often $0 with direct deposits)

## Monarch Money CSV Import Requirements (Research Findings)

Based on research of Monarch Money's official documentation:

### CSV Format Specification (CONFIRMED)
- **Required Format**: 9 columns in exact order (confirmed from official sample)
- **Column Order**:
  1. Date (YYYY-MM-DD format)
  2. Description
  3. Original Description (can be empty)
  4. Amount (decimal format)
  5. Transaction Type ("debit" or "credit")
  6. Category
  7. Account Name
  8. Labels (can be empty)
  9. Notes (can be empty)
- **Number Format**:
  - Positive numbers for income (+$100.00)
  - Negative numbers for expenses (-$100.00)
  - Use dash for negatives, not parentheses
- **Transaction Types**: "debit" for expenses/deductions, "credit" for income/deposits
- **Header Row**: Include header row as shown in official sample
- **Date Format**: YYYY-MM-DD (e.g., "2023-10-16")

### Transaction Structure Requirements
- **One row per component** (as requested)
- Each earning and deduction gets separate transaction row
- Maintains detailed breakdown for better financial tracking

### RSU Special Handling Requirements
- RSU vesting requires different treatment than regular payroll
- Heavy tax withholding on stock compensation
- Different categorization needed for stock-based income vs. salary
- May need separate transaction types for:
  - RSU income (positive)
  - Associated tax withholdings (negative)

### JSON Category Mapping Structure
- Structured configuration file for category mappings
- Support for different treatment of regular pay vs. RSU events
- Configurable account mappings for multiple deposit accounts

## Finalized Requirements

### 1. Output Format & Structure
- **CSV Format**: 9-column Monarch Money compatible format (CONFIRMED)
- **Transaction Granularity**: One row per earning/deduction component
- **Number Format**: Positive for income, negative for expenses
- **Transaction Types**: "credit" for income, "debit" for deductions
- **Header**: Include header row (Date,Description,Original Description,Amount,Transaction Type,Category,Account Name,Labels,Notes)

### 2. Transaction Categorization
- **JSON Configuration**: Category mapping file for flexible categorization
- **RSU Differentiation**: Special categories for stock compensation
- **Pre-tax Handling**: Separate categories for pre-tax vs. post-tax deductions
- **401k Treatment**: Mark as transfers to investment accounts

### 3. Date Handling
- **Primary Date**: Use Pay Date for transaction date
- **Format**: Monarch Money compatible date format

### 4. RSU Vesting Special Handling
- **Separate Processing**: Different logic for RSU vs. regular pay stubs
- **Tax Withholding**: Proper handling of heavy tax withholding on stock compensation
- **Categorization**: Distinct categories for stock-based compensation

### 5. Account Mapping
- **JSON Configuration**: User-configurable account mapping
- **Multiple Accounts**: Support for multiple deposit accounts (checking, savings)
- **Default Mapping**: Sensible defaults with override capability

### 6. Duplicate Prevention
- **Unique Identifier**: Include paystub advice number for deduplication
- **Date + Amount**: Secondary matching on date and amount
- **Skip Detection**: Logic to prevent duplicate imports

### 7. Configuration Files
- **category_mappings.json**: Transaction categorization rules
- **account_mappings.json**: Account mapping configuration
- **settings.json**: General script configuration

### 8. File Processing
- **Batch Processing**: Process directory of PDFs
- **Output**: Single CSV per paystub with standardized naming
- **Validation**: Verify gross pay = net pay + total deductions

## Technical Considerations
- PDF text extraction using libraries like PyPDF2, pdfplumber, or similar
- Parsing structured but potentially variable text layouts
- Handling currency formatting and decimal precision
- Date parsing and formatting for Monarch Money compatibility

## Success Criteria
1. Accurately extract all earning and deduction components from ADP PDFs
2. Generate properly formatted CSV for Monarch Money import
3. Maintain data integrity (totals balance)
4. Handle both regular pay and RSU vesting scenarios
5. Provide clear breakdown of gross pay components for financial tracking

---
*Please answer the clarification questions above so I can finalize the requirements and create an implementation plan.*