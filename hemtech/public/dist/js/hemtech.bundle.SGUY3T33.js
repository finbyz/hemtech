(() => {
  // ../hemtech/hemtech/public/js/controllers/transaction.js
  erpnext.TransactionController = class TransactionController extends erpnext.TransactionController {
    refresh() {
      erpnext.toggle_naming_series();
      erpnext.hide_company(this.frm);
      this.set_dynamic_labels();
      this.setup_sms();
      this.validate_has_items();
      erpnext.utils.view_serial_batch_nos(this.frm);
      this.set_route_options_for_new_doc();
      erpnext.toggle_serial_batch_fields(this.frm);
    }
    setup_quality_inspection() {
      if (![
        "Delivery Note",
        "Sales Invoice",
        "Purchase Receipt",
        "Purchase Invoice"
      ].includes(this.frm.doc.doctype)) {
        return;
      }
      const me = this;
      if (!this.frm.is_new() && this.frm.doc.docstatus === 0) {
        this.frm.add_custom_button(
          __("Quality Inspection(s)"),
          () => {
            me.make_quality_inspection();
          },
          __("Create")
        );
        this.frm.page.set_inner_btn_group_as_primary(__("Create"));
      }
      const inspection_type = ["Purchase Receipt", "Purchase Invoice"].includes(
        this.frm.doc.doctype
      ) ? "Incoming" : "Outgoing";
      let quality_inspection_field = this.frm.get_docfield("items", "quality_inspection");
      quality_inspection_field.get_route_options_for_new_doc = function(row) {
        if (me.frm.is_new())
          return {};
        return {
          inspection_type,
          reference_type: me.frm.doc.doctype,
          reference_name: me.frm.doc.name,
          item_code: row.doc.item_code,
          description: row.doc.description,
          item_serial_no: row.doc.serial_no ? row.doc.serial_no.split("\n")[0] : null,
          batch_no: row.doc.batch_no
        };
      };
      this.frm.set_query("quality_inspection", "items", function(doc, cdt, cdn) {
        let d = locals[cdt][cdn];
        return {
          filters: {
            docstatus: 1,
            inspection_type,
            reference_name: doc.name,
            item_code: d.item_code,
            merge: d.merge
          }
        };
      });
    }
  };
})();
//# sourceMappingURL=hemtech.bundle.SGUY3T33.js.map
