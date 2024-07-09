/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class StockReportController extends ListController {
   setup() {
       super.setup();
       console.log('test button js')
   }
//   OnTestClick() {
//       this.actionService.doAction({
//          type: 'ir.actions.act_window',
//          res_model: 'stock.report.wizard',
//          name:'Open Wizard',
//          view_mode: 'form',
//          view_type: 'form',
//          views: [[false, 'form']],
//          target: 'new',
//          res_id: false,
//      });
//   }
}
//registry.category("views").add("button_in_tree", { listView,
//    Controller: StockReportController,
//    buttonTemplate: "sale_custome.ListView.Buttons",
//});