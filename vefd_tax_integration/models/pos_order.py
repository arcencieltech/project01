# -*- coding: utf-8 -*-

import logging
from datetime import date, timedelta
from functools import partial
import psycopg2
import pytz
from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, Warning
import requests
import json
import datetime

_logger = logging.getLogger(__name__)

class CustomPosOrderCreate(models.Model):
    _inherit = "pos.order"
    
    vefd_TPIN = fields.Char("TPIN")
    vefd_refund_id = fields.Many2one("pos.order", string="Refund order")
    vefd_terminalID = fields.Char("Terminal ID")
    vefd_invoicecode = fields.Char("Invoice Code")
    vefd_invoicenumber = fields.Char("Invoice Number")
    vefd_fiscalcode = fields.Char("Fiscal Code")
    vefd_verificationUrl = fields.Char("Verification Url")
    vefd_date = fields.Char(string="VEFD Date")
    vefd_c2_code = fields.Char("VEFD Customer Code", copy=False)
#     0: Cash, 1: Card, 2: Cheque, 3: Electronic Transfer
    vefd_paymentmode = fields.Selection([('0','Cash'),('1','Card'),('2','Cheque'),('3','Electronic Transfer')], "VEFD Payment Mode")
    vefd_mtv_tax_price = fields.Float("VEFD MTV Tax Price")
    
    
    
    def vefd_tax_validate(self, data, order_id):
#         return True
#         refund_order = False
        
        refund_id = data['data'].get("refund_id", False)
        order_id = self.browse(order_id)
        
#         if "REFUND" in order_id.name and refund_id: 
        if refund_id:
#             refund_order = True
            refund_id = self.browse(int(refund_id))
            
        tax_ids = order_id.lines.mapped('tax_ids_after_fiscal_position')
        tax_label = False
        if tax_ids:
            tax_label = tax_ids.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code')
        if order_id and tax_label:
            payment_id = False
            vefd_paymentmode = False
            payment_id = order_id.payment_ids.mapped('payment_method_id')[0]
            
#             if data['data'].get("payment_method_id", False):
#                 payment_id = self.env['pos.payment.method'].browse(data.get("payment_method_id", False))
            
            if payment_id:
                if payment_id.is_cash_count:
                    vefd_paymentmode = 0
                else:
                    vefd_paymentmode = 3
                    
            
            if not payment_id:
                raise UserError(_("Please enter VEFD payment mode!"))
            OriginalInvoiceNumber = False
            OriginalInvoiceCode = False
            Memo = "POS Refund"
            TransactionType = 0
            SaleType = 0
#             if self.move_type == 'out_invoice':
#                 SaleType = 0
#                 TransactionType = 0
#          
#        Memo = str(self.narration) or str(self.ref)
#             elif self.move_type == 'out_refund':
#                 TransactionType = 1
#                 SaleType = 1
#                 if self.reversed_entry_id:
#                     OriginalInvoiceNumber = self.reversed_entry_id.vefd_invoicenumber
#                     OriginalInvoiceCode = self.reversed_entry_id.vefd_invoicecode
#                     Memo = str(self.narration) or str(self.ref)
                
            headers = {
                "Content-Type": "application/json"
                }
            
            vefd_id = self.env['vefd.credentials'].search([('active','=',True)], limit=1)
            if not vefd_id.terminal_id or not vefd_id.api_url:
                return False
            
            base_url = vefd_id.api_url
            call_api = "/api/InvoiceSign"
            
            if refund_id:
                if refund_id.vefd_invoicecode:
                    call_api = "/api/InvoiceReturn"
            
            BuyerAddress = "" 
            if order_id.partner_id:
                BuyerAddress = str(order_id.partner_id.street)+", " if order_id.partner_id.street else ""
                BuyerAddress += str(order_id.partner_id.street2)+", " if order_id.partner_id.street2 else ""
                BuyerAddress += str(order_id.partner_id.city)+", " if order_id.partner_id.city else ""
                BuyerAddress += str(order_id.partner_id.state_id.name)+", " if order_id.partner_id.state_id else ""
                BuyerAddress += str(order_id.partner_id.country_id.name)+"-" if order_id.partner_id.country_id else ""
                BuyerAddress += str(order_id.partner_id.zip) if order_id.partner_id.zip else ""
            
            
            d = datetime.datetime.now()
            data = {
                "TerminalId": vefd_id.terminal_id,
                "PosVendor": order_id.user_id.name,
                "PosSerialNumber": order_id.user_id.name,
                "IssueTime": str(d.year)+str(d.strftime("%m"))+str(d.strftime("%d"))+str(d.strftime("%H"))+str(d.strftime("%M"))+str(d.strftime("%S")),
                "TransactionType": TransactionType,
                "PaymentMode": int(vefd_paymentmode),
                "SaleType": SaleType,
                "Cashier": order_id.user_id.name,
#                 "BuyerName": order_id.partner_id.name if order_id.partner_id else "",
#                 "BuyerTPIN": order_id.partner_id.vat if order_id.partner_id else "", 
#                 "BuyerAddress": BuyerAddress, 
#                 "BuyerTel": order_id.partner_id.phone if order_id.partner_id else "",
#                 "OriginalInvoiceNumber": OriginalInvoiceNumber,
#                 "OriginalInvoiceCode": OriginalInvoiceCode,
#                 "Memo": Memo,
                "Currency-Type": order_id.currency_id.name,
                "Conversion-Rate": order_id.currency_id.name == 'ZMW' and 1 or order_id.currency_id.rate,
#                 "Conversion-Rate": 1,
#                 "Conversion-Rate": self.currency_id.name == 'ZMW' and 1 or 0,

                }
            
            if BuyerAddress:
                data.update({'BuyerAddress':BuyerAddress})
            if order_id.partner_id and order_id.partner_id.phone:
                data.update({'BuyerTel':order_id.partner_id.phone})
            if order_id.partner_id and order_id.partner_id.vat:
                data.update({'BuyerTPIN':order_id.partner_id.vat})
            if order_id.partner_id and order_id.partner_id.name:
                data.update({'BuyerName':order_id.partner_id.name})
                    
            items = []
            for line_id in order_id.lines:
                if line_id.tax_ids_after_fiscal_position.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code'):
                    TaxLabels = line_id.tax_ids_after_fiscal_position.filtered(lambda rec:rec.is_vefd_tax and rec.vefd_tax_code).mapped('vefd_tax_code')
                    
                    rrp = 0
                    line_id.onchange_vefd_product_id()
                    if 'B' in TaxLabels:
                        if line_id.vefd_rrp > 0:
                            rrp = line_id.vefd_rrp
                        if line_id.price_unit > rrp:
                            rrp = line_id.price_unit
                            
                        if not rrp:
                            raise UserError(_('Kindly enter Retail Price for MTV VEFD Taxes!'))
#                     if 'C2' in TaxLabels:
#                         if not order_id.vefd_c2_code:
#                             raise UserError(_('Kindly enter VEFD Customer code for C2 Taxes!'))
                    
                    
                    unit_price = line_id.price_unit * (1 - (line_id.discount / 100.0))
                    
                    
                    item_vals = {
                            "ItemId": line_id.product_id.id,
                            "Description": line_id.product_id.name,
#                             "BarCode": line_id.product_id.barcode,
                            "Quantity": abs(line_id.qty),
                            "UnitPrice": -round(unit_price, 2) if refund_id and refund_id.vefd_invoicecode else round(unit_price, 2),
                            "Discount": 0,
                            "TotalAmount": -round(round(unit_price, 2)*abs(line_id.qty), 2) if refund_id and refund_id.vefd_invoicecode else round(round(unit_price, 2)*abs(line_id.qty), 2),
                            "isTaxInclusive": True,
                            "RRP": rrp,
                            "TaxLabels":TaxLabels,
                            }
                    if line_id.product_id.barcode:
                        item_vals['BarCode'] = line_id.product_id.barcode
                    items.append(item_vals)
            data['Items'] = items
#             print(data)
            if refund_id:
                if refund_id.vefd_invoicecode:
                    order_id.vefd_refund_id = refund_id.id
                    data.update({
                        "TransactionType": 1,
                        "SaleType" : 1,
                        "OriginalInvoiceNumber" : refund_id.vefd_invoicenumber,
                        "OriginalInvoiceCode" : refund_id.vefd_invoicecode,
                        "Memo" : Memo,
                        })
                
            res = requests.post(vefd_id.api_url+call_api, data=json.dumps(data), headers=headers)
            
            if (res.status_code == 200):
#                 Response Text
#                 {"tpin":"1001734275","taxpayerName":"TONANO CASH AND CARRY LIMITED","address":"Plot 123B Langishe Road Second Class","vefdtime":"20210602021221",
#                  "terminalID":"010100000026","invoiceCode":"000210110000","invoiceNumber":"00001081","fiscalCode":"20522181115541420100","talkTime":null,
#                  "operator":null,"taxItems":[{"taxLabel":"A","categoryName":"STANDARD RATED","rate":0.16,"taxAmount":0.00}],
#                  "totalAmount":0.00,"verificationUrl":null}
                jres = json.loads(res.text)
#                 print(jres)

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
                order_id.write(inv_return_vals)
                
            else:
                raise UserError(_('Error sending data to VEFD!' + '\n' + res.text))
            return True
    
    @api.model
    def _process_order(self, order, draft, existing_order):
#         print(order)
        res = super(CustomPosOrderCreate, self)._process_order(order, draft, existing_order)
        self.vefd_tax_validate(order, res)
        return res
    
    
    def action_pos_order_invoice(self):
        res = super(CustomPosOrderCreate, self).action_pos_order_invoice()
        for rec in self:
            if rec.vefd_fiscalcode and rec.account_move:
                vefd_vals = {
                    "vefd_TPIN":rec.vefd_TPIN,
                    "vefd_terminalID":rec.vefd_terminalID,
                    "vefd_invoicecode":rec.vefd_invoicecode,
                    "vefd_invoicenumber":rec.vefd_invoicenumber,
                    "vefd_fiscalcode":rec.vefd_fiscalcode,
                    "vefd_verificationUrl":rec.vefd_verificationUrl,
                    "vefd_date":rec.vefd_date,
                    }
                rec.account_move.write(vefd_vals)
        return res
    
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    
    vefd_rrp = fields.Float("VEFD Retail Price")
    
    @api.onchange("product_id")
    def onchange_vefd_product_id(self):
        if self.product_id:
            self.vefd_rrp = self.product_id.vefd_MTV_rrp
    
    
class Company(models.Model):
    _inherit = "res.company"
    
    vefd_fiscalcode = fields.Char("Fiscal Code", default="Null")
    
    
    
    