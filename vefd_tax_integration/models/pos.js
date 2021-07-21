odoo.define('vefd_tax_integration.vefd_tax', function(require) {
"use strict";
    var rpc = require('web.rpc');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var utils = require('web.utils');
    var _t = core._t;
    var round_pr = utils.round_precision;
    var QWeb = core.qweb;
    var _super_order = models.Order;
    
    
    var vefd_order_id = function (event) {
            var vefd_order_id = $(this).val();
        }
    
    $(document).on('click', '#vefd_order_id', vefd_order_id);
    
    $(document).ready(function ($) {
   
		$("#vefd_order_id").change(function () {
							
			var vefd_order_id = $(this).val();
			//alert("test")
	    
	    });
	    
	 });
	
});

