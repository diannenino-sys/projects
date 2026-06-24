#!/usr/bin/env python3
"""
Settlement Report Aggregator
Processes multiple settlement CSV files and creates consolidated summaries by date periods
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

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
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
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
                    net_mdr_from_csv = float(row.get('net_mdr', 0))
                    
                    # Calculate MDR breakdown
                    mdr_breakdown = self.calculate_mdr_breakdown(abs(transaction_amount))
                    
                    # Store transaction
                    transaction_data = {
                        'settlement_txn_id': row.get('settlement_txn_id', ''),
                        'merchant_name': row.get('merchant_name', ''),
                        'transaction_type': transaction_type,
                        'transaction_datetime': row.get('transaction_datetime', ''),
                        'transaction_amount': transaction_amount,
                        'settle_amount': settle_amount,
                        'net_mdr_csv': net_mdr_from_csv,
                        **mdr_breakdown
                    }
                    
                    self.transactions.append(transaction_data)
                    
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
            'transactions': self.transactions
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


class SettlementAggregator:
    """Aggregate multiple settlement files with date-based compilation"""
    
    def __init__(self):
        self.daily_summaries = {}  # date -> summary
        self.all_transactions = []
    
    def process_directory(self, directory: str) -> Dict:
        """Process all CSV files in a directory"""
        csv_files = list(Path(directory).glob('*.csv'))
        
        if not csv_files:
            return {
                'status': 'error',
                'message': f'No CSV files found in {directory}'
            }
        
        for csv_file in sorted(csv_files):
            processor = SettlementProcessor(str(csv_file))
            result = processor.process()
            
            if result['status'] == 'success':
                settlement_date = result['settlement_date']
                self.daily_summaries[settlement_date] = result
                self.all_transactions.extend(result['transactions'])
        
        return {
            'status': 'success',
            'files_processed': len(csv_files),
            'daily_summaries': self.daily_summaries
        }
    
    def get_weekly_summary(self, start_date: datetime.date) -> Dict:
        """Get summary for a week starting from start_date"""
        week_summary = {
            'PAYMENT': self._init_summary_dict(),
            'REFUND': self._init_summary_dict(),
        }
        
        for i in range(7):
            current_date = (start_date + timedelta(days=i)).isoformat()
            if current_date in self.daily_summaries:
                daily = self.daily_summaries[current_date]['net_totals']
                for tx_type in ['PAYMENT', 'REFUND']:
                    daily_data = self.daily_summaries[current_date]['summary'][tx_type]
                    for key in week_summary[tx_type].keys():
                        week_summary[tx_type][key] += daily_data[key]
        
        return week_summary
    
    def get_15day_summary(self, start_date: datetime.date) -> Dict:
        """Get summary for 15 days starting from start_date"""
        period_summary = {
            'PAYMENT': self._init_summary_dict(),
            'REFUND': self._init_summary_dict(),
        }
        
        for i in range(15):
            current_date = (start_date + timedelta(days=i)).isoformat()
            if current_date in self.daily_summaries:
                daily_data = self.daily_summaries[current_date]['summary']
                for tx_type in ['PAYMENT', 'REFUND']:
                    for key in period_summary[tx_type].keys():
                        period_summary[tx_type][key] += daily_data[tx_type][key]
        
        return period_summary
    
    def get_monthly_summary(self, year: int, month: int) -> Dict:
        """Get summary for entire month"""
        period_summary = {
            'PAYMENT': self._init_summary_dict(),
            'REFUND': self._init_summary_dict(),
        }
        
        for day_str, daily_data in self.daily_summaries.items():
            try:
                date_obj = datetime.fromisoformat(day_str).date()
                if date_obj.year == year and date_obj.month == month:
                    for tx_type in ['PAYMENT', 'REFUND']:
                        for key in period_summary[tx_type].keys():
                            period_summary[tx_type][key] += daily_data['summary'][tx_type][key]
            except:
                pass
        
        return period_summary
    
    def get_grand_totals(self) -> Dict:
        """Get grand totals across all processed files"""
        grand_totals = {
            'PAYMENT': self._init_summary_dict(),
            'REFUND': self._init_summary_dict(),
        }
        
        for daily_data in self.daily_summaries.values():
            for tx_type in ['PAYMENT', 'REFUND']:
                for key in grand_totals[tx_type].keys():
                    grand_totals[tx_type][key] += daily_data['summary'][tx_type][key]
        
        return grand_totals
    
    @staticmethod
    def _init_summary_dict() -> Dict:
        """Initialize empty summary dictionary"""
        return {
            'count': 0,
            'transaction_amount': 0,
            'gross_mdr': 0,
            'mdr_vat_exclusive': 0,
            'mdr_vat': 0,
            'withholding_tax': 0,
            'net_mdr': 0,
            'settle_amount': 0,
        }
    
    @staticmethod
    def _calculate_net_totals(summary: Dict) -> Dict:
        """Calculate net totals from payment and refund data"""
        net_totals = {}
        for key in summary['PAYMENT'].keys():
            net_totals[key] = round(summary['PAYMENT'][key] - summary['REFUND'][key], 2)
        return net_totals
    
    def generate_consolidated_html(self, output_file: str):
        """Generate comprehensive HTML dashboard with all period summaries"""
        grand_totals = self.get_grand_totals()
        grand_net = self._calculate_net_totals(grand_totals)
        
        # Build daily rows
        daily_rows = ""
        for date_str in sorted(self.daily_summaries.keys()):
            daily = self.daily_summaries[date_str]
            net = daily['net_totals']
            daily_rows += f"""
            <tr>
                <td>{date_str}</td>
                <td class="amount">${net['transaction_amount']:,.2f}</td>
                <td class="amount">${net['gross_mdr']:,.2f}</td>
                <td class="amount">${net['mdr_vat_exclusive']:,.2f}</td>
                <td class="amount">${net['mdr_vat']:,.2f}</td>
                <td class="amount">${net['withholding_tax']:,.2f}</td>
                <td class="amount">${net['net_mdr']:,.2f}</td>
                <td class="amount">${net['settle_amount']:,.2f}</td>
            </tr>
            """
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settlement Report - Consolidated Summary</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            font-size: 1.8em;
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        
        .metric-card h3 {{
            color: #667eea;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        
        .metric-card .value {{
            font-size: 1.8em;
            color: #333;
            font-weight: bold;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.95em;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .amount {{
            text-align: right;
            font-weight: 500;
        }}
        
        .total-row {{
            background: #f0f0f0;
            font-weight: bold;
        }}
        
        .total-row td {{
            border-top: 2px solid #667eea;
            border-bottom: 2px solid #667eea;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }}
        
        .alert {{
            background: #e8f5e9;
            border-left: 5px solid #4caf50;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}
        
        .alert p {{
            color: #2e7d32;
            margin: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Settlement Report - Consolidated Summary</h1>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="content">
            <div class="alert">
                <p>✓ All summaries shown are NET TOTALS (Refunds deducted from Payments)</p>
            </div>
            
            <!-- Grand Totals Section -->
            <div class="section">
                <h2>🎯 Grand Totals (All Data)</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <h3>Transaction Count</h3>
                        <div class="value">{grand_net['count']:,}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Total Transaction Amount</h3>
                        <div class="value">${grand_net['transaction_amount']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Gross MDR</h3>
                        <div class="value">${grand_net['gross_mdr']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>MDR (VAT Excl.)</h3>
                        <div class="value">${grand_net['mdr_vat_exclusive']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>MDR VAT (12%)</h3>
                        <div class="value">${grand_net['mdr_vat']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Withholding Tax (2%)</h3>
                        <div class="value">${grand_net['withholding_tax']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Net MDR</h3>
                        <div class="value">${grand_net['net_mdr']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Settlement Amount</h3>
                        <div class="value">${grand_net['settle_amount']:,.2f}</div>
                    </div>
                </div>
            </div>
            
            <!-- Daily Breakdown Table -->
            <div class="section">
                <h2>📅 Daily Breakdown</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Settlement Date</th>
                            <th class="amount">Transaction Amount</th>
                            <th class="amount">Gross MDR</th>
                            <th class="amount">MDR (VAT Excl.)</th>
                            <th class="amount">MDR VAT (12%)</th>
                            <th class="amount">Withholding Tax</th>
                            <th class="amount">Net MDR</th>
                            <th class="amount">Settlement Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {daily_rows}
                        <tr class="total-row">
                            <td><strong>TOTAL</strong></td>
                            <td class="amount"><strong>${grand_net['transaction_amount']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['gross_mdr']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['mdr_vat_exclusive']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['mdr_vat']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['withholding_tax']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['net_mdr']:,.2f}</strong></td>
                            <td class="amount"><strong>${grand_net['settle_amount']:,.2f}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Settlement Report Automation • Consolidated Summary Report</p>
        </div>
    </div>
</body>
</html>
        """
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            print(f"Error writing HTML: {e}")
    
    def generate_consolidated_csv(self, output_file: str):
        """Generate comprehensive CSV with all data"""
        grand_totals = self.get_grand_totals()
        grand_net = self._calculate_net_totals(grand_totals)
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(['Settlement Report - Consolidated Summary'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])
                
                # Grand Totals
                writer.writerow(['GRAND TOTALS (All Data - NET TOTALS)'])
                writer.writerow(['Metric', 'Amount'])
                for key, value in grand_net.items():
                    writer.writerow([key.replace('_', ' ').title(), f"${value:,.2f}"])
                writer.writerow([])
                
                # Daily Breakdown
                writer.writerow(['DAILY BREAKDOWN'])
                writer.writerow(['Settlement Date', 'Transaction Amount', 'Gross MDR', 'MDR (VAT Excl.)',
                               'MDR VAT (12%)', 'Withholding Tax (2%)', 'Net MDR', 'Settlement Amount'])
                
                for date_str in sorted(self.daily_summaries.keys()):
                    daily = self.daily_summaries[date_str]
                    net = daily['net_totals']
                    writer.writerow([
                        date_str,
                        f"${net['transaction_amount']:,.2f}",
                        f"${net['gross_mdr']:,.2f}",
                        f"${net['mdr_vat_exclusive']:,.2f}",
                        f"${net['mdr_vat']:,.2f}",
                        f"${net['withholding_tax']:,.2f}",
                        f"${net['net_mdr']:,.2f}",
                        f"${net['settle_amount']:,.2f}",
                    ])
                
                # Total row
                writer.writerow(['TOTAL',
                               f"${grand_net['transaction_amount']:,.2f}",
                               f"${grand_net['gross_mdr']:,.2f}",
                               f"${grand_net['mdr_vat_exclusive']:,.2f}",
                               f"${grand_net['mdr_vat']:,.2f}",
                               f"${grand_net['withholding_tax']:,.2f}",
                               f"${grand_net['net_mdr']:,.2f}",
                               f"${grand_net['settle_amount']:,.2f}"])
        
        except Exception as e:
            print(f"Error writing CSV: {e}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python settlement_aggregator.py <input_directory> [output_directory]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'settlement_results'
    
    Path(output_dir).mkdir(exist_ok=True)
    
    # Process all files
    aggregator = SettlementAggregator()
    result = aggregator.process_directory(input_dir)
    
    if result['status'] == 'success':
        # Generate consolidated outputs
        html_output = Path(output_dir) / 'CONSOLIDATED_SUMMARY.html'
        csv_output = Path(output_dir) / 'CONSOLIDATED_SUMMARY.csv'
        
        aggregator.generate_consolidated_html(str(html_output))
        aggregator.generate_consolidated_csv(str(csv_output))
        
        print(f"✓ Processing complete!")
        print(f"✓ Files processed: {result['files_processed']}")
        print(f"✓ HTML report: {html_output}")
        print(f"✓ CSV report: {csv_output}")
        print(f"\nDaily summaries:")
        for date_str in sorted(aggregator.daily_summaries.keys()):
            net = aggregator.daily_summaries[date_str]['net_totals']
            print(f"  {date_str}: ${net['settle_amount']:,.2f}")
    else:
        print(f"✗ Error: {result['message']}")
        sys.exit(1)
