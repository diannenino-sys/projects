#!/usr/bin/env python3
"""
Settlement Report to Google Sheets Uploader
Processes large settlement CSV files and uploads to Google Sheet
Handles files up to 400MB+ with automatic tax calculations
"""

import csv
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SettlementProcessor:
    """Process settlement reports with tax calculations"""
    
    VAT_RATE = 0.12  # 12%
    MDR_RATE = 0.014  # 1.4%
    WITHHOLDING_TAX_RATE = 0.02  # 2%
    
    def __init__(self, csv_file_path: str):
        self.csv_file = csv_file_path
        self.settlement_date = None
        self.transactions = []
        self.summary = {
            'PAYMENT': {
                'count': 0,
                'transaction_amount': 0,
                'gross_mdr': 0,
                'mdr_vat_exclusive': 0,
                'mdr_vat': 0,
                'withholding_tax': 0,
                'net_mdr': 0,
                'settle_amount': 0,
            },
            'REFUND': {
                'count': 0,
                'transaction_amount': 0,
                'gross_mdr': 0,
                'mdr_vat_exclusive': 0,
                'mdr_vat': 0,
                'withholding_tax': 0,
                'net_mdr': 0,
                'settle_amount': 0,
            }
        }
    
    def calculate_mdr_breakdown(self, transaction_amount: float) -> Dict[str, float]:
        """
        Calculate MDR breakdown with tax components
        
        1. Gross MDR = Transaction Amount × 1.4%
        2. MDR VAT Exclusive = Gross MDR ÷ 1.12
        3. MDR VAT = Gross MDR - MDR VAT Exclusive
        4. Withholding Tax = MDR VAT Exclusive × 2%
        5. Net MDR = Gross MDR - Withholding Tax
        """
        gross_mdr = transaction_amount * self.MDR_RATE
        mdr_vat_exclusive = gross_mdr / (1 + self.VAT_RATE)
        mdr_vat = gross_mdr - mdr_vat_exclusive
        withholding_tax = mdr_vat_exclusive * self.WITHHOLDING_TAX_RATE
        net_mdr = gross_mdr - withholding_tax
        
        return {
            'gross_mdr': round(gross_mdr, 2),
            'mdr_vat_exclusive': round(mdr_vat_exclusive, 2),
            'mdr_vat': round(mdr_vat, 2),
            'withholding_tax': round(withholding_tax, 2),
            'net_mdr': round(net_mdr, 2),
        }
    
    def process(self) -> Dict:
        """Process the settlement CSV file"""
        try:
            row_count = 0
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    row_count += 1
                    
                    # Progress indicator for large files
                    if row_count % 50000 == 0:
                        print(f"   Processing row {row_count}...")
                    
                    transaction_type = row.get('transaction_type', '').strip().upper()
                    
                    if transaction_type not in ['PAYMENT', 'REFUND']:
                        continue
                    
                    # Extract settlement date from first valid row
                    if not self.settlement_date:
                        settle_date_str = row.get('settle_date', '')
                        if settle_date_str:
                            try:
                                self.settlement_date = datetime.strptime(settle_date_str, '%Y%m%d').date()
                            except:
                                self.settlement_date = datetime.now().date()
                    
                    transaction_amount = float(row.get('transaction_amount', 0))
                    settle_amount = float(row.get('settle_amount', 0))
                    
                    # Calculate MDR breakdown
                    mdr_breakdown = self.calculate_mdr_breakdown(abs(transaction_amount))
                    
                    # Update summary
                    summary_type = transaction_type
                    self.summary[summary_type]['count'] += 1
                    self.summary[summary_type]['transaction_amount'] += abs(transaction_amount)
                    self.summary[summary_type]['gross_mdr'] += mdr_breakdown['gross_mdr']
                    self.summary[summary_type]['mdr_vat_exclusive'] += mdr_breakdown['mdr_vat_exclusive']
                    self.summary[summary_type]['mdr_vat'] += mdr_breakdown['mdr_vat']
                    self.summary[summary_type]['withholding_tax'] += mdr_breakdown['withholding_tax']
                    self.summary[summary_type]['net_mdr'] += mdr_breakdown['net_mdr']
                    self.summary[summary_type]['settle_amount'] += settle_amount
            
            print(f"✓ Processed {row_count} rows")
            return self._calculate_net_totals()
        
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _calculate_net_totals(self) -> Dict:
        """Calculate net totals (payments minus refunds)"""
        net_totals = {}
        
        for key in self.summary['PAYMENT'].keys():
            payment_value = self.summary['PAYMENT'][key]
            refund_value = self.summary['REFUND'][key]
            net_totals[key] = round(payment_value - refund_value, 2)
        
        return {
            'status': 'success',
            'file': self.csv_file,
            'settlement_date': str(self.settlement_date) if self.settlement_date else 'unknown',
            'processed_at': datetime.now().isoformat(),
            'summary': self.summary,
            'net_totals': net_totals,
        }
    
    @property
    def net_totals(self):
        """Get net totals property"""
        net_totals = {}
        for key in self.summary['PAYMENT'].keys():
            payment_value = self.summary['PAYMENT'][key]
            refund_value = self.summary['REFUND'][key]
            net_totals[key] = round(payment_value - refund_value, 2)
        return net_totals


class GoogleSheetsUploader:
    """Upload settlement data to Google Sheet"""
    
    def __init__(self, credentials_file: str, sheet_id: str):
        """
        Initialize uploader with Google credentials
        
        Args:
            credentials_file: Path to service account JSON file
            sheet_id: Google Sheet ID (from URL)
        """
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.client = None
        self.sheet = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file, scope)
            
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.sheet_id)
            
            print("✓ Google Sheets authenticated successfully")
            return True
        
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return False
    
    def add_daily_record(self, settlement_date: str, net_totals: Dict):
        """Add a daily settlement record to the sheet"""
        try:
            worksheet = self.sheet.worksheet("Daily Settlement")
            
            # Check if date already exists
            existing_rows = worksheet.col_values(1)  # Settlement Date column
            
            if settlement_date in existing_rows:
                # Update existing row
                row_index = existing_rows.index(settlement_date) + 1
                row_values = [
                    settlement_date,
                    net_totals['count'],
                    f"${net_totals['transaction_amount']:,.2f}",
                    f"${net_totals['gross_mdr']:,.2f}",
                    f"${net_totals['mdr_vat_exclusive']:,.2f}",
                    f"${net_totals['mdr_vat']:,.2f}",
                    f"${net_totals['withholding_tax']:,.2f}",
                    f"${net_totals['net_mdr']:,.2f}",
                    f"${net_totals['settle_amount']:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
                worksheet.update(f"A{row_index}:J{row_index}", [row_values])
                print(f"✓ Updated record for {settlement_date}")
            else:
                # Add new row
                row_values = [
                    settlement_date,
                    net_totals['count'],
                    f"${net_totals['transaction_amount']:,.2f}",
                    f"${net_totals['gross_mdr']:,.2f}",
                    f"${net_totals['mdr_vat_exclusive']:,.2f}",
                    f"${net_totals['mdr_vat']:,.2f}",
                    f"${net_totals['withholding_tax']:,.2f}",
                    f"${net_totals['net_mdr']:,.2f}",
                    f"${net_totals['settle_amount']:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
                worksheet.append_row(row_values)
                print(f"✓ Added new record for {settlement_date}")
            
            return True
        
        except Exception as e:
            print(f"✗ Failed to add daily record: {e}")
            return False
    
    def update_summary_sheets(self):
        """Update summary sheets with formulas"""
        try:
            # The summary sheets should have formulas that auto-calculate
            # based on the Daily Settlement sheet
            print("✓ Summary sheets will auto-update with formulas")
            return True
        except Exception as e:
            print(f"✗ Failed to update summaries: {e}")
            return False


def main():
    print("=" * 70)
    print("Settlement Report to Google Sheets Uploader")
    print("=" * 70)
    
    if len(sys.argv) < 4:
        print("\nUsage:")
        print("  python upload_to_sheets.py <csv_file> <sheet_id> <credentials_file>")
        print("\nExample:")
        print("  python upload_to_sheets.py settlement_2026-06-01.csv 1a2b3c4d5e6f7g8h credentials.json")
        print("\nWhere:")
        print("  csv_file: Path to your settlement CSV file (can be 350-400MB)")
        print("  sheet_id: Google Sheet ID (from URL: docs.google.com/spreadsheets/d/{SHEET_ID})")
        print("  credentials_file: Path to Google service account JSON file")
        print("\nSetup Instructions:")
        print("  1. Create a Google Sheet with tabs: Daily Settlement, Weekly, Monthly, Grand Totals")
        print("  2. Get service account credentials from Google Cloud Console")
        print("  3. Share the Google Sheet with the service account email")
        print("  4. Run this script with your CSV file and sheet ID")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    sheet_id = sys.argv[2]
    credentials_file = sys.argv[3]
    
    # Verify files exist
    if not Path(csv_file).exists():
        print(f"✗ CSV file not found: {csv_file}")
        sys.exit(1)
    
    if not Path(credentials_file).exists():
        print(f"✗ Credentials file not found: {credentials_file}")
        print("\nGet credentials from Google Cloud Console:")
        print("  1. Go to: https://console.cloud.google.com/")
        print("  2. Create a new project")
        print("  3. Enable Google Sheets API")
        print("  4. Create a Service Account")
        print("  5. Download JSON credentials")
        sys.exit(1)
    
    # Show file sizes
    csv_size_mb = Path(csv_file).stat().st_size / (1024 * 1024)
    print(f"\n📊 Processing Settlement Report")
    print(f"   File: {Path(csv_file).name}")
    print(f"   Size: {csv_size_mb:.2f}MB")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Process CSV
    print("🔍 Reading and processing CSV file...")
    processor = SettlementProcessor(csv_file)
    result = processor.process()
    
    if result['status'] != 'success':
        print(f"✗ Processing failed: {result['message']}")
        sys.exit(1)
    
    print(f"   Settlement Date: {result['settlement_date']}")
    print(f"   Status: {result['status']}")
    print()
    
    # Upload to Google Sheets
    print("📤 Uploading to Google Sheets...")
    uploader = GoogleSheetsUploader(credentials_file, sheet_id)
    
    if not uploader.authenticate():
        print("✗ Failed to authenticate with Google Sheets")
        sys.exit(1)
    
    if not uploader.add_daily_record(result['settlement_date'], result['net_totals']):
        print("✗ Failed to upload data")
        sys.exit(1)
    
    uploader.update_summary_sheets()
    
    # Show summary
    net_totals = result['net_totals']
    print("\n" + "=" * 70)
    print("📊 Settlement Summary")
    print("=" * 70)
    print(f"Settlement Date: {result['settlement_date']}")
    print(f"Transaction Count: {net_totals['count']:,}")
    print(f"Total Transaction Amount: ${net_totals['transaction_amount']:,.2f}")
    print(f"Gross MDR (1.4%): ${net_totals['gross_mdr']:,.2f}")
    print(f"MDR (VAT Excl.): ${net_totals['mdr_vat_exclusive']:,.2f}")
    print(f"MDR VAT (12%): ${net_totals['mdr_vat']:,.2f}")
    print(f"Withholding Tax (2%): ${net_totals['withholding_tax']:,.2f}")
    print(f"Net MDR: ${net_totals['net_mdr']:,.2f}")
    print(f"Settlement Amount: ${net_totals['settle_amount']:,.2f}")
    print("=" * 70)
    print("\n✅ Upload complete!")
    print(f"📍 View your data: https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == '__main__':
    main()
