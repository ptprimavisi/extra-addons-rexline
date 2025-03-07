/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

class SystrayIcon extends Component {
    setup() {
        this.addCustomFloatCSS();
    }

    // Menambahkan CSS secara dinamis untuk custom float left
    addCustomFloatCSS() {
        // Membuat tag <style> untuk menambahkan CSS
        const style = document.createElement("style");
        style.innerHTML = `
            .custom_float_field {
                text-align: left !important;
            }
        `;

        // Menambahkan tag <style> ke dalam <head> di halaman
        document.head.appendChild(style);
    }
}

export default SystrayIcon;
