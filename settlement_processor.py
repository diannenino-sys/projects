#!/usr/bin/env python3
"""
Settlement Processor - Core processing logic
Handles CSV parsing and tax calculations
"""

import csv
from datetime import datetime
from typing import Dict

class SettlementProcessor:
    """Process settlement reports with tax calculations"""
    
    VAT_RATE = 0.12  # 12%
    MDR_RATE = 0.014  # 1.4%
    WITHHOLDING_TAX_RATE = 0.02  # 2%
    
    def __init__(self, csv_file_path: str):
        self.csv_file = csv_file_path
        self.settlement_date = None
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
        """Calculate MDR breakdown with tax components"""
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
                    
                    if row_count % 50000 == 0:
                        print(f"   Processing row {row_count}...")
                    
                    transaction_type = row.get('transaction_type', '').strip().upper()
                    
                    if transaction_type not in ['PAYMENT', 'REFUND']:
                        continue
                    
                    if not self.settlement_date:
                        settle_date_str = row.get('settle_date', '')
                        if settle_date_str:
                            try:
                                self.settlement_date = datetime.strptime(settle_date_str, '%Y%m%d').date()
                            except:
                                self.settlement_date = datetime.now().date()
                    
                    transaction_amount = float(row.get('transaction_amount', 0))
                    settle_amount = float(row.get('settle_amount', 0))
                    
                    mdr_breakdown = self.calculate_mdr_breakdown(abs(transaction_amount))
                    
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
            return {'status': 'error', 'message': str(e)}
    
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
