odoo.define('vefd_tax_integration.OrderManagementScreen', function (require) {
    'use strict';

    const { useContext, useRef } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    const OrderFetcher = require('point_of_sale.OrderFetcher');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const contexts = require('point_of_sale.PosContext');

    class OrderManagementScreen extends ControlButtonsMixin(IndependentToOrderScreen) {
        constructor() {
            super(...arguments);
            useListener('close-screen', this._close);
            useListener('set-numpad-mode', this._setNumpadMode);
            useListener('click-order', this._onClickOrder);
            useListener('refund-click-pay', this._onClickPay);
            useListener('next-page', this._onNextPage);
            useListener('prev-page', this._onPrevPage);
            useListener('search', this._onSearch);
            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                useWithBarcode: true,
            });
            this.numpadMode = 'quantity';
            OrderFetcher.setComponent(this);
            OrderFetcher.setConfigId(this.env.pos.config_id);
            this.orderManagementContext = useContext(contexts.orderManagement);
            this.receiptRef = useRef('order-receipt');
        }
        mounted() {
            OrderFetcher.on('update', this, this.render);
            this.env.pos.get('orders').on('add remove', this.render, this);

            // calculate how many can fit in the screen.
            // It is based on the height of the header element.
            // So the result is only accurate if each row is just single line.
            const flexContainer = this.el.querySelector('.flex-container');
            const cpEl = this.el.querySelector('.control-panel');
            const headerEl = this.el.querySelector('.order-row.header');
            const val = Math.trunc(
                (flexContainer.offsetHeight - cpEl.offsetHeight - headerEl.offsetHeight) /
                    headerEl.offsetHeight
            );
            OrderFetcher.setNPerPage(val);

            // Fetch the order after mounting so that order management screen
            // is shown while fetching.
            setTimeout(() => OrderFetcher.fetch(), 0);
        }
        willUnmount() {
            OrderFetcher.off('update', this);
            this.env.pos.get('orders').off('add remove', null, this);
        }
        get selectedClient() {
            const order = this.orderManagementContext.selectedOrder;
            return order ? order.get_client() : null;
        }
        get orders() {
            return OrderFetcher.get();
        }
        async _setNumpadMode(event) {
            const { mode } = event.detail;
            this.numpadMode = mode;
            NumberBuffer.reset();
        }
        _onNextPage() {
            OrderFetcher.nextPage();
        }
        _onPrevPage() {
            OrderFetcher.prevPage();
        }
        _onSearch({ detail: domain }) {
            OrderFetcher.setSearchDomain(domain);
            OrderFetcher.setPage(1);
            OrderFetcher.fetch();
        }
        
        _onClickPay() {
            this.showScreen('PaymentScreen');
        }
        _onClickOrder({ detail: clickedOrder }) {
        	
        	
	        	//alert(clickedOrder);
	        	console.log(clickedOrder.backendId);
	        	
	        	var self = this;
	        	
	        	console.log(this.env.session.user_context['uid']);
	        	
	        	this.rpc({
	                	model: 'res.users',
	                	method: 'check_pos_manager_rights',
	                	args: [self.env.session.user_context['uid']],
		            }).then(function (results) {
		            	if(results){
								$(".refund-click-pay").show();
								
								
								self.rpc({
					                model: 'pos.order.line',
					                method: 'search_read',
					                kwargs: {
					                        domain: [['order_id','=',clickedOrder.backendId]],
					                        fields: [],
					                        context: self.env.session.user_context
					                    },
						            }).then(function (results) {
						            	//alert(results);
						            	console.log(results);
						            	
						            	let currentOrder = self.env.pos.get_order();
						            	currentOrder.set_refund_id(clickedOrder.backendId)
						            	currentOrder.get_orderlines().forEach(function(line) {
						            		line.order.remove_orderline(line);
						            	});
						            	results.forEach(function(line) {
						            		console.log(line);
						            		//const ProductScreen = new ProductScreen();
						            		var product1el = self.env.pos.db.get_product_by_id(line.product_id[0]);
						            		//const options = ProductScreen._getAddProductOptions(product1el);
						            		var options = {}
						            		console.log(product1el);
						            		currentOrder.add_product(product1el, options);
						            		currentOrder.get_selected_orderline().set_quantity(-line.qty)
						            		currentOrder.get_selected_orderline().set_unit_price(line.price_unit)
						            		currentOrder.get_selected_orderline().set_discount(line.discount)
						            	});
						            	
						            	
						            });
								
								
							}else{
								$(".refund-click-pay").hide();
							}
							
		            });
	        	
        
            if (!clickedOrder || clickedOrder.locked) {
                this.orderManagementContext.selectedOrder = clickedOrder;
                let currentPOSOrder = this.env.pos.get_order();
                if (clickedOrder.attributes.client){
                    currentPOSOrder.set_client(clickedOrder.attributes.client);
                }
                if (clickedOrder.fiscal_position){
                    currentPOSOrder.fiscal_position = clickedOrder.fiscal_position;
                }
                if (clickedOrder.pricelist){
                    currentPOSOrder.set_pricelist(clickedOrder.pricelist);
                }
            } else {
                this._setOrder(clickedOrder);
            }
        }
        /**
         * @param {models.Order} order
         */
        _setOrder(order) {
            this.env.pos.set_order(order);
            if (order === this.env.pos.get_order()) {
                this.close();
            }
        }
        _close() {
            let currentOrder = this.env.pos.get_order();
            if (currentOrder){
                currentOrder.set_client(false);
                currentOrder.fiscal_position = false;
                currentOrder.set_pricelist(this.env.pos.default_pricelist);
            }
            this.close();
        }
    }
    OrderManagementScreen.template = 'OrderManagementScreen';
    OrderManagementScreen.hideOrderSelector = true;

    Registries.Component.add(OrderManagementScreen);

    return OrderManagementScreen;
});
