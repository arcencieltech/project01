from odoo import models, fields, api
import base64
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
from odoo.exceptions import UserError
from odoo.tools.translate import _
import datetime
from dateutil import relativedelta
import re
import requests

import logging
_logger = logging.getLogger(__name__)



class product(models.Model):
    _inherit ="product.template"
    
    vefd_MTV_rrp = fields.Float("MTV Retail Price")
        
    
    
    
                    