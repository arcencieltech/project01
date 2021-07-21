
from odoo import api, fields, models, _
import re
import requests
import os
import hmac
import hashlib
import datetime


import logging

_logger = logging.getLogger(__name__)

class VEFDCredentials(models.Model):
    _name = 'vefd.credentials'

    name = fields.Char(string="Name", required=True)
    terminal_id = fields.Char(string="Terminal ID", required=True)
    api_url = fields.Char(string="API base URL", required=True)
    active = fields.Boolean(default=True)
    tax_cron_interval_number = fields.Integer(default=1, help="Repeat every x.")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='months')
    tax_cron_id = fields.Many2one('ir.cron', string="Tax Cron")
    
    @api.onchange("interval_type","tax_cron_interval_number")
    def onchange_interval_number(self):
        if self.interval_type and self.tax_cron_id:
            self.tax_cron_id.interval_type = self.interval_type
        if self.tax_cron_interval_number and self.tax_cron_id:
            self.tax_cron_id.interval_number = self.tax_cron_interval_number
    
    
    