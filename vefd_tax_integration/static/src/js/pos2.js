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
   
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            var receipt = _super_order.export_for_printing.bind(this)();
            var order = this.pos.get_order();            
            
			
            receipt = _.extend(receipt, {
                'receipt': _.extend(receipt, {
                'vefd_fiscalcode': 'fiscalcode'
                })
            });

            return receipt;
        },
    });

});

