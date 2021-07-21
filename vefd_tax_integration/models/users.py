# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError



class resusers(models.Model):
    _inherit = 'res.users'
    

    def check_pos_manager_rights(self):
        if self.has_group('point_of_sale.group_pos_manager'):
            return 'true';
        else:
            return '';
