/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

//var rpc = require('web.rpc');

class SystrayIcon extends Component {
 setup() {
   super.setup(...arguments);
   this.action = useService("action");
   try {
        jsonrpc('/sale/get_inquiry', {}).then(result => {
            console.log('panjang',result.length)
            if (result && result.length > 0) {
                    $('#button_clip').attr('data-bs-toggle', 'dropdown')
                    $('#card_menu').append('<ul id="dropdown_ul" class="dropdown-menu" aria-labelledby="button_clip"></ul>');

                    var c = 0;
                    result.forEach(function(count) {
                        console.log('data',count);
                        $('#dropdown_ul').append('<li><a class="dropdown-item" href="' +'web#id='+count['id'] + '&cids=1&menu_id=385&action=580&model=request.price&view_type=form'+ '">'+count['name']+'</a></li>');
//                        http://localhost:8069/web#id=22&cids=1&menu_id=420&action=652&model=request.price&view_type=form
//                        var ele = $('<a role="menuitem" href="'+'/web#id=' + order['id'] + '&view_type=form&model=sale.order'+'" class="dropdown-item">'+order['name']+'</a>')
//                        self.$('#order_list').append(ele);
//                        self.$('#isi').html(result.length)
                        c += 1;
                    });
                    $('#button_clip').append('<span class="o_MessagingMenu_counter badge badge-pill" id="isi">'+c+'</span>');

                }
            // Handle the result or perform any additional logic
            console.log(result)
        });
    } catch (error) {
        // Handle errors
        console.error('Error:', error);
    }

 }

 _onClick() {
    console.log("Button clicked!");
//    try {
//        jsonrpc('/sale/get_inquiry', {}).then(result => {
//            // Handle the result or perform any additional logic
//            console.log(result)
//            this.action.doAction({
//                type: "ir.actions.act_window",
//                name: "Purchase Order",
//                res_model: "purchase.order",
//                view_mode: "form",
//                views: [[false, "form"]],
//                target: "new",
//            });
//        });
//    } catch (error) {
//        // Handle errors
//        console.error('Error:', error);
//    }
 }
}

SystrayIcon.template = "systray_icon";
export const systrayItem = {
 Component: SystrayIcon,
};
registry.category("systray").add("SystrayIcon", systrayItem, { sequence: 1 });