# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosController(http.Controller):
    
    
    @http.route(['/get_vefd_qrcode'], type='http', auth='public', csrf=False)
    def get_vefd_qrcode(self, **post):
        qr_code = False
        pos_no = post.get('pos_no')
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
            if pos_id and pos_id.vefd_fiscalcode:
                qr_code = "Verification Url:"+str(pos_id.vefd_verificationUrl)+'\n'+\
                          "TPIN:"+str(pos_id.vefd_TPIN)+'\n'+\
                          "Invoice Code:"+str(pos_id.vefd_invoicecode)+'\n'+\
                          "Invoice No:"+str(pos_id.vefd_invoicenumber)+'\n'+\
                          "Terminal ID:"+str(pos_id.vefd_terminalID)+'\n'+\
                          "Fiscal Code:"+str(pos_id.vefd_fiscalcode)+'\n'+\
                          "Date:"+str(pos_id.vefd_date)
                        
        return str(qr_code)
    
    @http.route(['/get_vefd_mtvtax_price'], type='http', auth='public', csrf=False)
    def get_vefd_mtvtax_price(self, **post):
        pos_no = post.get('pos_no')
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
        return str(pos_id.vefd_mtv_tax_price)
    
    @http.route(['/get_vefd_totalmtvtax_price'], type='http', auth='public', csrf=False)
    def get_vefd_totalmtvtax_price(self, **post):
        pos_no = post.get('pos_no', False)
        tax_total = float(post.get('tax_total', 0))
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
        return str(round(pos_id.vefd_mtv_tax_price+tax_total, 2))
    
    @http.route(['/get_vefd_fiscalcode'], type='http', auth='public', csrf=False)
    def get_vefd_fiscalcode(self, **post):
        vefd_fiscalcode = False
        pos_no = post.get('pos_no')
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
            vefd_fiscalcode = pos_id.vefd_fiscalcode and "Fiscal Code:"+str(pos_id.vefd_fiscalcode) or ""
        return str(vefd_fiscalcode)
    
    
#     data.update({'vefd_fiscalcode':pos_id.vefd_fiscalcode,'vefd_invoicecode':pos_id.vefd_invoicecode,'vefd_invoicenumber':pos_id.vefd_invoicenumber})

    @http.route(['/get_vefd_invoicecode'], type='http', auth='public', csrf=False)
    def get_vefd_invoicecode(self, **post):
        vefd_invoicecode = False
        pos_no = post.get('pos_no')
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
            if pos_id.vefd_invoicecode:
                vefd_invoicecode = pos_id.vefd_invoicecode and "Invoice Code:"+str(pos_id.vefd_invoicecode) or ""
        return str(vefd_invoicecode)
    
    @http.route(['/get_vefd_invoicenumber'], type='http', auth='public', csrf=False)
    def get_vefd_invoicenumber(self, **post):
        vefd_invoicenumber = False
        pos_no = post.get('pos_no')
        if pos_no:
            pos_id = request.env['pos.order'].sudo().search([('pos_reference','=',pos_no)], limit=1)
            if pos_id.vefd_invoicenumber:
                vefd_invoicenumber = pos_id.vefd_invoicenumber and "Invoice Number:"+str(pos_id.vefd_invoicenumber) or ""
        return str(vefd_invoicenumber)
    
    @http.route(['/get_vefd_details'], type='http', auth="public", csrf=False)
    def get_vefd_details(self, **post):
#         print(post)
        options = "<option value=''>-Select order to refund-</option>"
        
        order_ids = request.env['pos.order'].sudo().search([('vefd_invoicecode','!=',False)])
#         vefd_order_search_id = False
#         if post.get("vefd_order_search_id", False):
#             vefd_order_search_id = request.env['pos.order'].sudo().search([('name','ilike',post.get("vefd_order_search_id", False))])
        
        for order_id in order_ids:
            if post.get("vefd_order_search_id", False) and request.env['pos.order'].sudo().search([('id','=',order_id.id), ('name','ilike',post.get("vefd_order_search_id", False))], limit=1):
                options+="<option value="+str(order_id.id)+" selected='true'"+">"+order_id.name+"</option>"
            else:
                options+="<option value="+str(order_id.id)+">"+order_id.name+"</option>"
                    
        return options
    
    
    @http.route(['/get_refund_details'], type='http', auth="public", csrf=False)
    def get_refund_details(self, **post):
#         print(post)
#         print(request.session)
        session_info = request.env['ir.http'].session_info()
#         print(session_info)
        options = "<option value=''>-Select order to refund-</option>"
        
        order_ids = request.env['pos.order'].sudo().search([('vefd_invoicecode','!=',False)])
        
        for order_id in order_ids:
                options+="<option value="+str(order_id.id)+">"+order_id.name+"</option>"
                    
        return options
        
        
    
    
    
    
    