   odoo.define('vefd_tax_integration.models', function (require) {
        "use strict";
        
        var ajax = require('web.ajax');
        const Registries = require('point_of_sale.Registries');
        var field_utils = require('web.field_utils');
        
        var models = require('point_of_sale.models');
        
        var posmodel_super = models.PosModel.prototype;
        
        models.PosModel = models.PosModel.extend({
        
        
	        _save_to_server: function (order) {
	            var self = this;
	            var refund_id = '';
	            if (document.getElementById('vefd_order_id') != null) {
				    refund_id = document.getElementById("vefd_order_id").value;
				}
	            
	            this.session.user_context['refund_id'] = refund_id
	            
	            return posmodel_super._save_to_server.apply(self, [order]);
	        },
	        
        });
        
        
        var Orderline_super = models.Orderline.prototype;
        
        models.Orderline = models.Orderline.extend({
	        
	        initialize: function(attr,options){
	        	this.pos = options.pos;
		        this.vefd_rrp = 0;
		        this.vefd_rrpStr = '0';
		        return Orderline_super.initialize.call(this,attr,options);
		    },
		    
		    set_rrp: function(rrp){
		        var parsed_rrp = isNaN(parseFloat(rrp)) ? 0 : field_utils.parse.float('' + rrp);
		        var o_rrp = parsed_rrp;
		        this.vefd_rrp = o_rrp;
		        this.vefd_rrpStr = '' + o_rrp;
		        //alert(o_rrp);
		        this.trigger('change',this);
		    },
		    
	        get_rrp: function(){
		        return this.vefd_rrp;
		    },
		    get_rrp_str: function(){
		        return this.vefd_rrpStr;
		    },
		    
		    
		    init_from_JSON: function (json) {
	            Orderline_super.init_from_JSON.apply(this, arguments);
	            this.set_rrp(json.vefd_rrp);
	        },
	        
	        export_as_JSON: function () {
	            var json = Orderline_super.export_as_JSON.apply(this, arguments);
	
	            return _.extend(json, {
	                'vefd_rrp': this.get_rrp()
	            });
	        },
	        
	        
	        export_for_printing: function () {
	            var json = Orderline_super.export_for_printing.apply(this, arguments);
	
	            return _.extend(json, {
	                'vefd_rrp': this.get_rrp()
	            });
	        }
        
	        
        
        });


		var Order_super = models.Order.prototype;
        
        models.Order = models.Order.extend({
	        
	        initialize: function(attr,options){
	        	this.pos = options.pos;
		        this.refund_id = 0;
		        this.vefd_fiscalcode = '';
		        this.vefd_invoicecode = '';
		        this.vefd_invoicenumber = '';
		        return Order_super.initialize.call(this,attr,options);
		    },
		    
		    set_refund_id: function(refund_id){
		        this.refund_id = refund_id;
		        this.trigger('change',this);
		    },
		    
	        get_refund_id: function(){
		        return this.refund_id;
		    },
		    remove_refund_id: function(){
		        this.refund_id = 0;
		    },
		    
		    
		    init_from_JSON: function (json) {
	            Order_super.init_from_JSON.apply(this, arguments);
	            this.set_refund_id(json.refund_id);
	            //this.set_vefd_fiscalcode();
	        },
	        
	        export_as_JSON: function () {
	            var json = Order_super.export_as_JSON.apply(this, arguments);
	
	            return _.extend(json, {
	                'refund_id': this.get_refund_id(),
	                //'vefd_fiscalcode': this.get_vefd_fiscalcode()
	            });
	        },
	        
	        /* set_vefd_fiscalcode: function(){
	        	var self = this;
		        ajax.post('/get_vefd_fiscalcode', {'pos_no':'number'}).then(function (result) {
		        	if (document.getElementById('order_number') != null) {
		        		document.getElementById('order_number').value = '6666'
					}
                })
                if (document.getElementById('order_number') != null) {
		        	this.vefd_fiscalcode = document.getElementById('order_number').value;
		        	this.trigger('change',this);
					}
                
		        
		    }, */
	        
	        /* get_vefd_fiscalcode: function(){
		        //return this.vefd_fiscalcode;
		        return this.vefd_fiscalcode;
		         ajax.post('/get_vefd_fiscalcode', {'pos_no':'number'}).then(function (result) {
		        	if (document.getElementById('order_number') != null) {
		        		document.getElementById('order_number').value = '988'
					}
                })
                if (document.getElementById('order_number') != null) {
		        	return document.getElementById('order_number').value;
					} 
		    }, */

		    
	        export_for_printing: function () {
	            var json = Order_super.export_for_printing.apply(this, arguments);
				
	            return _.extend(json, {
	                'refund_id': this.get_refund_id(),
	                //'vefd_fiscalcode': this.get_vefd_fiscalcode(),
	            });
	        }
	        
	        
        });


        
        
        const ProductScreen = require('point_of_sale.ProductScreen');
        
        
	    const ProductScreen_ex = ProductScreen => class extends ProductScreen {
	    
	    
	    	_onClickPay() {
	    		this.currentOrder.remove_refund_id()
            	this.showScreen('PaymentScreen');
        	}
	    
	        _setValue(val) {
	        
	            if (this.currentOrder.get_selected_orderline()) {
	                if (this.state.numpadMode === 'quantity') {
	                    this.currentOrder.get_selected_orderline().set_quantity(val);
	                } else if (this.state.numpadMode === 'discount') {
	                    this.currentOrder.get_selected_orderline().set_discount(val);
	                } else if (this.state.numpadMode === 'rrp') {
	                    //alert('set value haha');
	                    this.currentOrder.get_selected_orderline().set_rrp(val);
	                } else if (this.state.numpadMode === 'price') {
	                    var selected_orderline = this.currentOrder.get_selected_orderline();
	                    selected_orderline.price_manually_set = true;
	                    selected_orderline.set_unit_price(val);
	                }
	                if (this.env.pos.config.iface_customer_facing_display) {
	                    this.env.pos.send_current_order_to_customer_facing_display();
	                }
	            }
	        }
	        
		    };

    	Registries.Component.extend(ProductScreen, ProductScreen_ex);

    	return ProductScreen_ex;
    	
    	
        const NumpadWidget = require('point_of_sale.NumpadWidget');
        
        
        
	    const PosFrNumpadWidget = NumpadWidget => class extends NumpadWidget {
	        changeMode(mode) {
				
	            if (!this.hasPriceControlRights && mode === 'price') {
	                return;
	            }
	            if (!this.hasManualDiscount && mode === 'discount') {
	                return;
	            }
	            if (!this.hasManualDiscount && mode === 'rrp') {
	                return;
	            }
	            this.trigger('set-numpad-mode', { mode });
	        }
		    };

    	Registries.Component.extend(NumpadWidget, PosFrNumpadWidget);

    	return NumpadWidget;
        
 
     });