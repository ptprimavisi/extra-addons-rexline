/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

class SystrayIconInquiry extends Component {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");

        // Memanggil data untuk inquiry
        try {
            jsonrpc('/inquiry/get_inquiry_no_request', {}).then(result => {
                if (result && result.length > 0) {
                    $('#button_clip').attr('data-bs-toggle', 'dropdown');
                    $('#card_menu').append('<ul id="dropdown_ul" class="dropdown-menu" aria-labelledby="button_clip"></ul>');

                    let count_inq = 0;
                    result.forEach(function (count) {
                        console.log('data', count, count_inq);
                        // Menambahkan item ke dropdown dengan ID untuk digunakan saat klik
                        $('#dropdown_ul').append('<li><a class="dropdown-item" href="' + 'web#id=' + count['id'] + '&cids=1&menu_id=543&action=777&model=request.price&view_type=form' + '">' + count['name'] + '</a></li>');
                        count_inq += 1;
                    });
                    $('#button_clip').append('<span class="o_MessagingMenu_counter badge badge-pill" id="isi">' + count_inq + '</span>');
                }
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }
}

SystrayIconInquiry.template = "systray_icon_inquiry";
export const systrayItemInquiry = {
    Component: SystrayIconInquiry,
};
registry.category("systray").add("SystrayIconInquiry", systrayItemInquiry, { sequence: 1 });
