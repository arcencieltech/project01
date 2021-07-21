# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from json import dumps
import datetime

import json
import requests

class AccountMove(models.Model):
    _inherit = "account.move"
    
    vefd_TPIN = fields.Char("TPIN", copy=False)
    vefd_terminalID = fields.Char("Terminal ID" , copy=False)
    vefd_invoicecode = fields.Char("Invoice Code", copy=False)
    vefd_invoicenumber = fields.Char("Invoice Number", copy=False)
    vefd_fiscalcode = fields.Char("Fiscal Code", copy=False)
    vefd_verificationUrl = fields.Char("Verification Url" , copy=False)
    vefd_date = fields.Char(string="VEFD Date")
#     0: Cash, 1: Card, 2: Cheque, 3: Electronic Transfer
    vefd_c2_code = fields.Char("VEFD Customer Code", copy=False)
    vefd_paymentmode = fields.Selection([('0','Cash'),('1','Card'),('2','Cheque'),('3','Electronic Transfer')], "VEFD Payment Mode", default='0')
    vefd_mtv_tax_price = fields.Float("VEFD MTV Tax Price")
    
    
#     @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id')
#     def _compute_invoice_taxes_by_group(self):
#         ''' Helper to get the taxes grouped according their account.tax.group.
#         This method is only used when printing the invoice.
#         '''
#         res = super(AccountMove, self)._compute_invoice_taxes_by_group()
#         
#         for rec in self:
#             for amount_by_group in rec.amount_by_group:
#                 if rec.vefd_fiscalcode and amount_by_group[0] == 'MTVs':
#                     amount_by_group[3] = rec.vefd_mtv_tax_price
#         
# #         return res

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id')
    def _compute_invoice_taxes_by_group(self):
        ''' Helper to get the taxes grouped according their account.tax.group.
        This method is only used when printing the invoice.
        '''
        for move in self:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id)
            tax_balance_multiplicator = -1 if move.is_inbound(True) else 1
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in tax_lines:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += tax_balance_multiplicator * (line.amount_currency if line.currency_id else line.balance)
                tax_key_add_base = tuple(move._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                        amount = line.company_currency_id._convert(line.tax_base_amount, line.currency_id, line.company_id, line.date or fields.Date.context_today(self))
                    else:
                        amount = line.tax_base_amount
                    res[line.tax_line_id.tax_group_id]['base'] += amount
                    # The base should be added ONCE
                    done_taxes.add(tax_key_add_base)

            # At this point we only want to keep the taxes with a zero amount since they do not
            # generate a tax line.
            zero_taxes = set()
            for line in move.line_ids:
                for tax in line.tax_ids.flatten_taxes_hierarchy():
                    if tax.tax_group_id not in res or tax.tax_group_id in zero_taxes:
                        res.setdefault(tax.tax_group_id, {'base': 0.0, 'amount': 0.0})
                        res[tax.tax_group_id]['base'] += tax_balance_multiplicator * (line.amount_currency if line.currency_id else line.balance)
                        zero_taxes.add(tax.tax_group_id)

            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_by_group = [(
                group.name, amounts['amount'],
                amounts['base'],
                formatLang(lang_env, move.vefd_mtv_tax_price if group.name == 'MTVs' and move.vefd_fiscalcode else amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                group.id
            ) for group, amounts in res]
            
            
    def vefd_tax_validate(self):
        for rec in self:
            if rec.move_type not in ['out_invoice','out_refund']:
                return True 
            
            if rec.vefd_invoicecode:
                return True
                
            sale_id = False
            tax_label = False
            if rec.invoice_line_ids.mapped("sale_line_ids"):
                sale_id = rec.invoice_line_ids.mapped("sale_line_ids").mapped('order_id')[0]
            tax_ids = rec.invoice_line_ids.mapped('tax_ids')
            if tax_ids:
                tax_label = tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code')
            if sale_id and tax_label:
                
    #             if not rec.vefd_paymentmode:
    #                 raise UserError(_("Please enter VEFD payment mode!"))
                OriginalInvoiceNumber = False
                OriginalInvoiceCode = False
                Memo = "empty"
                TransactionType = 0
                if rec.move_type == 'out_invoice':
                    SaleType = 0
                    TransactionType = 0
                    Memo = str(rec.narration) or str(rec.ref)
                elif rec.move_type == 'out_refund':
                    TransactionType = 1
                    SaleType = 1
                    if rec.reversed_entry_id or rec.reversal_move_id:
                        reversal_move_id = rec.reversed_entry_id or rec.reversal_move_id[0]
                        OriginalInvoiceNumber = reversal_move_id.vefd_invoicenumber
                        OriginalInvoiceCode = reversal_move_id.vefd_invoicecode
                        Memo = str(rec.ref) or str(rec.narration) or ""
                    
                headers = {
                    "Content-Type": "application/json"
                    }
                
                vefd_id = rec.env['vefd.credentials'].search([('active','=',True)], limit=1)
                if not vefd_id.terminal_id or not vefd_id.api_url:
                    return False
                
                base_url = vefd_id.api_url
                call_api = "/api/InvoiceSign"
                
                if rec.move_type == 'out_refund':
                    call_api = "/api/InvoiceReturn"
                
                BuyerAddress = "" 
                if rec.partner_id:
                    BuyerAddress = str(rec.partner_id.street)+", " if rec.partner_id.street else ""
                    BuyerAddress += str(rec.partner_id.street2)+", " if rec.partner_id.street2 else ""
                    BuyerAddress += str(rec.partner_id.city)+", " if rec.partner_id.city else ""
                    BuyerAddress += str(rec.partner_id.state_id.name)+", " if rec.partner_id.state_id else ""
                    BuyerAddress += str(rec.partner_id.country_id.name)+"-" if rec.partner_id.country_id else ""
                    BuyerAddress += str(rec.partner_id.zip) if rec.partner_id.zip else ""
                
                d = datetime.datetime.now()
                data = {
                    "TerminalId": vefd_id.terminal_id,
                    "PosVendor": sale_id.user_id.name,
                    "PosSerialNumber": sale_id.user_id.name,
                    "IssueTime": str(d.year)+str(d.strftime("%m"))+str(d.strftime("%d"))+str(d.strftime("%H"))+str(d.strftime("%M"))+str(d.strftime("%S")),
                    "TransactionType": TransactionType,
                    "PaymentMode": int(rec.vefd_paymentmode) or 0,
                    "SaleType": SaleType,
                    "Cashier": sale_id.user_id.name,
                    "OriginalInvoiceNumber": OriginalInvoiceNumber,
                    "OriginalInvoiceCode": OriginalInvoiceCode,
                    "Memo": Memo,
                    "Currency-Type": rec.currency_id.name,
                    "Conversion-Rate": rec.currency_id.name == 'ZMW' and 1 or rec.currency_id.rate,
#                     "BuyerName": rec.partner_id.name if rec.partner_id else "",
#                     "BuyerTPIN": rec.partner_id.vat if rec.partner_id else "", 
#                     "BuyerAddress": BuyerAddress, 
#                     "BuyerTel": rec.partner_id.phone if rec.partner_id else "", 
#                     "buyer-vat": rec.partner_id.phone if rec.partner_id else "", 
    #                 "Conversion-Rate": 1,
    #                 "Conversion-Rate": rec.currency_id.name == 'ZMW' and 1 or 0,
    
                    }
                if BuyerAddress:
                    data.update({'BuyerAddress':BuyerAddress})
                if rec.partner_id and rec.partner_id.phone:
                    data.update({'BuyerTel':rec.partner_id.phone})
                if rec.partner_id and rec.partner_id.vat:
                    data.update({'BuyerTPIN':rec.partner_id.vat})
                if rec.partner_id and rec.partner_id.name:
                    data.update({'BuyerName':rec.partner_id.name})
                items = []
                for line_id in rec.invoice_line_ids:
                    if line_id.tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code'):
                        TaxLabels = line_id.tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code')
                        rrp = 0
                        
                        if 'B' in TaxLabels:
#                             if not line_id.vefd_rrp:
#                                 line_id.onchange_vefd_product_id()
#                             if line_id.vefd_rrp > 0:
#                                 rrp = line_id.vefd_rrp
#                             if line_id.price_unit > rrp:
#                                 rrp = line_id.price_unit
                            if line_id.vefd_rrp > 0:
                                rrp = line_id.vefd_rrp
                            if not rrp:
                                raise UserError(_('Kindly enter Retail Price for MTV VEFD Taxes!'))
                            
                        if 'C2' in TaxLabels:
                            if not rec.vefd_c2_code:
                                raise UserError(_('Kindly enter VEFD Customer code for C2 Taxes!'))
    #                     unit_price = line_id.price_unit * ((100-line_id.discount) / 100)
                        unit_price = line_id.price_unit * (1 - (line_id.discount / 100.0))
                        item_vals = {
                                "ItemId": line_id.product_id.id,
                                "Description": line_id.product_id.name,
    #                             "BarCode": line_id.product_id.barcode,
                                "Quantity": line_id.quantity,
                                "UnitPrice": -round(unit_price, 2) if rec.move_type == 'out_refund' else round(unit_price, 2),
                                "Discount": 0,
                                "TotalAmount": -round(round(unit_price, 2)*line_id.quantity, 2) if rec.move_type == 'out_refund' else round(round(unit_price, 2)*line_id.quantity, 2),
                                "isTaxInclusive": True,
                                "RRP": rrp,
                                "TaxLabels":TaxLabels,
                                }
                        if line_id.product_id.barcode:
                            item_vals['BarCode'] = line_id.product_id.barcode
                        items.append(item_vals)
                data['Items'] = items
#                 print(data)
                res = requests.post(vefd_id.api_url+call_api, data=json.dumps(data), headers=headers)
                
                if (res.status_code == 200):
    #                 Response Text
    #                 {"tpin":"1001734275","taxpayerName":"TONANO CASH AND CARRY LIMITED","address":"Plot 123B Langishe Road Second Class","vefdtime":"20210602021221",
    #                  "terminalID":"010100000026","invoiceCode":"000210110000","invoiceNumber":"00001081","fiscalCode":"20522181115541420100","talkTime":null,
    #                  "operator":null,"taxItems":[{"taxLabel":"A","categoryName":"STANDARD RATED","rate":0.16,"taxAmount":0.00}],
    #                  "totalAmount":0.00,"verificationUrl":null}
                    jres = json.loads(res.text)
#                     print(jres)
    #                 timestamp = datetime.datetime.fromtimestamp(jres.get("vefdtime",False))
    #                 timestamp = datetime.datetime.fromtimestamp(20210602021221)
                    if not jres.get("fiscalCode",False):
                        raise UserError(_('Error sending data to VEFD!' + '\n' + res.text))
                    
                    tax_price = 0
                    if jres.get("taxItems",False):
                        tax_price = 0
                        
                        for tax in jres.get("taxItems",False):
                            if tax.get("taxLabel", False) == 'B':
                                tax_price = tax_price + float(tax.get("taxAmount", 0))
                    
                    inv_return_vals = {
                                "vefd_TPIN":jres.get("tpin",False),
                                "vefd_terminalID":jres.get("terminalID",False),
                                "vefd_invoicecode":jres.get("invoiceCode",False),
                                "vefd_invoicenumber":jres.get("invoiceNumber",False),
                                "vefd_fiscalcode":jres.get("fiscalCode",False),
                                "vefd_verificationUrl":jres.get("verificationUrl",False),
                                "vefd_date":jres.get("vefdtime",False),
                                "vefd_mtv_tax_price":tax_price,
                                }
                    rec.write(inv_return_vals)
                    
                else:
                    raise UserError(_('Error sending data to VEFD!' + '\n' + res.text))
                return True
            
            elif tax_label:
                
                OriginalInvoiceNumber = False
                OriginalInvoiceCode = False
                Memo = "empty"
                TransactionType = 0
                if rec.move_type == 'out_invoice':
                    SaleType = 0
                    TransactionType = 0
                    Memo = str(rec.narration) or str(rec.ref)
                elif rec.move_type == 'out_refund':
                    TransactionType = 1
                    SaleType = 1
                    if rec.reversed_entry_id or rec.reversal_move_id:
                        reversal_move_id = rec.reversed_entry_id or rec.reversal_move_id[0]
                        OriginalInvoiceNumber = reversal_move_id.vefd_invoicenumber
                        OriginalInvoiceCode = reversal_move_id.vefd_invoicecode
                        Memo = str(rec.ref) or str(rec.narration) or ""
                    
                headers = {
                    "Content-Type": "application/json"
                    }
                
                vefd_id = rec.env['vefd.credentials'].search([('active','=',True)], limit=1)
                if not vefd_id.terminal_id or not vefd_id.api_url:
                    return False
                
                base_url = vefd_id.api_url
                call_api = "/api/InvoiceSign"
                
                if rec.move_type == 'out_refund':
                    call_api = "/api/InvoiceReturn"
                
                BuyerAddress = "" 
                if rec.partner_id:
                    BuyerAddress = str(rec.partner_id.street)+", " if rec.partner_id.street else ""
                    BuyerAddress += str(rec.partner_id.street2)+", " if rec.partner_id.street2 else ""
                    BuyerAddress += str(rec.partner_id.city)+", " if rec.partner_id.city else ""
                    BuyerAddress += str(rec.partner_id.state_id.name)+", " if rec.partner_id.state_id else ""
                    BuyerAddress += str(rec.partner_id.country_id.name)+"-" if rec.partner_id.country_id else ""
                    BuyerAddress += str(rec.partner_id.zip) if rec.partner_id.zip else ""
                
                
                d = datetime.datetime.now()
                data = {
                    "TerminalId": vefd_id.terminal_id,
                    "PosVendor": rec.invoice_user_id.name,
                    "PosSerialNumber": rec.invoice_user_id.name,
                    "IssueTime": str(d.year)+str(d.strftime("%m"))+str(d.strftime("%d"))+str(d.strftime("%H"))+str(d.strftime("%M"))+str(d.strftime("%S")),
                    "TransactionType": TransactionType,
                    "PaymentMode": int(rec.vefd_paymentmode) or 0,
                    "SaleType": SaleType,
                    "Cashier": rec.invoice_user_id.name,
                    "OriginalInvoiceNumber": OriginalInvoiceNumber,
                    "OriginalInvoiceCode": OriginalInvoiceCode,
                    "Memo": Memo,
                    "Currency-Type": rec.currency_id.name,
                    "Conversion-Rate": rec.currency_id.name == 'ZMW' and 1 or rec.currency_id.rate,
#                     "BuyerName": rec.partner_id.name if rec.partner_id else "",
#                     "BuyerTPIN": rec.partner_id.vat if rec.partner_id else "", 
#                     "BuyerAddress": BuyerAddress, 
#                     "BuyerTel": rec.partner_id.phone if rec.partner_id else "",
    #                 "Conversion-Rate": 1,
    #                 "Conversion-Rate": rec.currency_id.name == 'ZMW' and 1 or 0,
    
                    }
                if BuyerAddress:
                    data.update({'BuyerAddress':BuyerAddress})
                if rec.partner_id and rec.partner_id.phone:
                    data.update({'BuyerTel':rec.partner_id.phone})
                if rec.partner_id and rec.partner_id.vat:
                    data.update({'BuyerTPIN':rec.partner_id.vat})
                if rec.partner_id and rec.partner_id.name:
                    data.update({'BuyerName':rec.partner_id.name})
                
                items = []
                for line_id in rec.invoice_line_ids:
                    if line_id.tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code'):
                        TaxLabels = line_id.tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code')
                        rrp = 0
                        
                        if 'B' in TaxLabels:
#                             if not line_id.vefd_rrp:
#                                 line_id.onchange_vefd_product_id()
#                             if line_id.vefd_rrp > 0:
#                                 rrp = line_id.vefd_rrp
#                             if line_id.price_unit > rrp:
#                                 rrp = line_id.price_unit
                            if line_id.vefd_rrp > 0:
                                rrp = line_id.vefd_rrp
                            if not rrp:
                                raise UserError(_('Kindly enter Retail Price for MTV VEFD Taxes!'))
                        if 'C2' in TaxLabels:
                            if not rec.vefd_c2_code:
                                raise UserError(_('Kindly enter VEFD Customer code for C2 Taxes!'))
    #                     unit_price = line_id.price_unit * ((100-line_id.discount) / 100)
                        unit_price = line_id.price_unit * (1 - (line_id.discount / 100.0))
                        item_vals = {
                                "ItemId": line_id.product_id.id,
                                "Description": line_id.product_id.name,
    #                             "BarCode": line_id.product_id.barcode,
                                "Quantity": line_id.quantity,
                                "UnitPrice": -round(unit_price, 2) if rec.move_type == 'out_refund' else round(unit_price, 2),
                                "Discount": 0,
                                "TotalAmount": -round(round(unit_price, 2)*line_id.quantity, 2) if rec.move_type == 'out_refund' else round(round(unit_price, 2)*line_id.quantity, 2),
                                "isTaxInclusive": True,
                                "RRP": rrp,
                                "TaxLabels":TaxLabels,
                                }
                        if line_id.product_id.barcode:
                            item_vals['BarCode'] = line_id.product_id.barcode
                        items.append(item_vals)
                data['Items'] = items
#                 print(data)
                res = requests.post(vefd_id.api_url+call_api, data=json.dumps(data), headers=headers)
                
                if (res.status_code == 200):
    #                 Response Text
    #                 {"tpin":"1001734275","taxpayerName":"TONANO CASH AND CARRY LIMITED","address":"Plot 123B Langishe Road Second Class","vefdtime":"20210602021221",
    #                  "terminalID":"010100000026","invoiceCode":"000210110000","invoiceNumber":"00001081","fiscalCode":"20522181115541420100","talkTime":null,
    #                  "operator":null,"taxItems":[{"taxLabel":"A","categoryName":"STANDARD RATED","rate":0.16,"taxAmount":0.00}],
    #                  "totalAmount":0.00,"verificationUrl":null}
                    jres = json.loads(res.text)
#                     print(jres)
    #                 timestamp = datetime.datetime.fromtimestamp(jres.get("vefdtime",False))
    #                 timestamp = datetime.datetime.fromtimestamp(20210602021221)
                    if not jres.get("fiscalCode",False):
                        raise UserError(_('Error sending data to VEFD!' + '\n' + res.text))
                    
                    is_MTV = False
                    tax_price = 0
                    if jres.get("taxItems",False):
                        tax_price = 0
                        
                        for tax in jres.get("taxItems",False):
                            if tax.get("taxLabel", False) == 'B':
                                is_MTV = True
                                tax_price = tax_price + float(tax.get("taxAmount", 0))
                    
                    inv_return_vals = {
                                "vefd_TPIN":jres.get("tpin",False),
                                "vefd_terminalID":jres.get("terminalID",False),
                                "vefd_invoicecode":jres.get("invoiceCode",False),
                                "vefd_invoicenumber":jres.get("invoiceNumber",False),
                                "vefd_fiscalcode":jres.get("fiscalCode",False),
                                "vefd_verificationUrl":jres.get("verificationUrl",False),
                                "vefd_date":jres.get("vefdtime",False),
                                "vefd_mtv_tax_price":tax_price,
                                }
                    rec.write(inv_return_vals)
                    
#                     Invoice Query: {base-url}/api/invoiceretrieve
#                     call_api = "/api/invoiceretrieve"
#                     data = {
#                         "id":vefd_id.terminal_id,
#                         "code":rec.vefd_invoicecode,
#                         "number":rec.vefd_invoicenumber,
#                         }
#                     invoiceretrieve = requests.post(vefd_id.api_url+call_api, data=json.dumps(data), headers=headers)
#                     print(invoiceretrieve.text)
                    
                else:
                    raise UserError(_('Error sending data to VEFD!' + '\n' + res.text))
                return True
            
            
#     def action_post(self):
#         res = super(AccountMove, self).action_post()
#         self.vefd_tax_validate()
#         return res
    
    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft)
        self.vefd_tax_validate()
        return res
    
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    vefd_rrp = fields.Float("VEFD Retail Price")
    vefd_tax_mtv_price = fields.Float("VEFD MTV Tax Price")
    
#     @api.onchange("product_id")
#     def onchange_vefd_product_id(self):
#         if self.product_id:
#             self.vefd_rrp = self.product_id.vefd_MTV_rrp
             
        
        
        
        
    
        
            
            