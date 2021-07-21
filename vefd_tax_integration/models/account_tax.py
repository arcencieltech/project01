# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError
import json
import requests

import math
import logging


class VefdAccountTaxType(models.Model):
    _name = 'vefd.account.tax.type'
    
    name = fields.Char("Code")

class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_vefd_tax = fields.Boolean("Is VEFD Tax?")
    vefd_tax_type_id = fields.Many2one("vefd.account.tax.type", string="VEFD Tax Type")
    vefd_tax_name = fields.Char(string="VEFD Tax Name")
    vefd_tax_code = fields.Char("Code")
    vefd_tax_rate = fields.Float(string="VEFD Rate")
    
    def get_vefd_taxes(self):
        
        vefd_id = self.env['vefd.credentials'].search([('active','=',True)], limit=1)
        if not vefd_id or not vefd_id.terminal_id or not vefd_id.api_url:
            return False
        
        data = {
            "id": vefd_id.terminal_id,
            }
        headers = {
            "Content-Type": "application/json"
            }
        base_url = vefd_id.api_url
        call_api = "/api/Status"
#         vefd_tax_ids = self.env['account.tax'].search([('is_vefd_tax','=',True)])
        res = requests.post(vefd_id.api_url+call_api, data=json.dumps(data), headers=headers)
        
        if (res.status_code == 200):

            jres = json.loads(res.text)
            
            for vefd_tax in jres:
                tax_type = vefd_tax.get("tax-type", False)
                if vefd_tax.get("category", False) and tax_type:
                    for cate in vefd_tax.get("category", False):
                        vefd_tax_id = self.env['account.tax'].search([('is_vefd_tax','=',True), ('type_tax_use','=','sale'),('vefd_tax_type_id.name','=',tax_type),('vefd_tax_code','=',cate.get("tax-code", False))], limit=1)
                        if vefd_tax_id:
                            vefd_tax_id.write({"vefd_tax_name":cate.get("tax-name", False), 'amount':float(cate.get("tax-rate", False))*100, 'vefd_tax_rate':cate.get("tax-rate", False)})
        else:
            raise UserError(_('Error getting Taxes!' + '\n' + res.text))
        return True
    
    