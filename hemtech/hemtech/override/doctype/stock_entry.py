from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as _StockEntry
import frappe
from erpnext.stock.get_item_details import get_default_cost_center
from frappe.utils import flt, cstr


from spinning.doc_events.bom import get_bom_items_as_dict # Finbyz Changes
from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items # Finbyz Changes
class StockEntry(_StockEntry):
    def get_sle_for_target_warehouse(self, sl_entries, finished_item_row):
        """Override to set recalculate_rate=1 for scrap/secondary items.

        In core ERPNext, only finished items and transfer items get recalculate_rate=1.
        Scrap items (is_legacy_scrap_item) and secondary items (type set from BOM)
        are skipped, causing their SLE incoming_rate to go out of sync with the
        Stock Entry's valuation_rate during repost.
        """
        super().get_sle_for_target_warehouse(sl_entries, finished_item_row)

        if self.purpose not in ("Manufacture", "Repack"):
            return

        for sle in sl_entries:
            if sle.get("actual_qty", 0) <= 0:
                continue
            # Find the matching Stock Entry Detail row
            voucher_detail_no = sle.get("voucher_detail_no")
            for d in self.items:
                if d.name == voucher_detail_no and (d.get("is_legacy_scrap_item") or d.get("type") or d.get("secondary_item_type")):
                    sle["recalculate_rate"] = 1
                    break

    def get_bom_raw_materials(self, qty):
        # from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

        # item dict = { item_code: {qty, description, stock_uom} }
        item_dict = get_bom_items_as_dict(
            self.bom_no,
            self.company,
            qty=qty,
            fetch_exploded=self.use_multi_level_bom,
            fetch_qty_in_stock_uom=False,
        )

        used_alternative_items = get_used_alternative_items(
            subcontract_order_field=self.subcontract_data.order_field, work_order=self.work_order
        )
        for item in item_dict.values():
            # if source warehouse presents in BOM set from_warehouse as bom source_warehouse
            if item["allow_alternative_item"]:
                item["allow_alternative_item"] = frappe.db.get_value(
                    "Work Order", self.work_order, "allow_alternative_item"
                )

            item.from_warehouse = self.from_warehouse or item.source_warehouse or item.default_warehouse
            if item.item_code in used_alternative_items:
                alternative_item_data = used_alternative_items.get(item.item_code)
                item.item_code = alternative_item_data.item_code
                item.item_name = alternative_item_data.item_name
                item.stock_uom = alternative_item_data.stock_uom
                item.uom = alternative_item_data.uom
                item.conversion_factor = alternative_item_data.conversion_factor
                item.description = alternative_item_data.description

        return item_dict
    
    def add_to_stock_entry_detail(self, item_dict, bom_no=None):
        precision = frappe.get_precision("Stock Entry Detail", "qty")
        for d in item_dict:
            item_row = item_dict[d]

            child_qty = flt(item_row["qty"], precision)
            if (
                not self.is_return
                and child_qty <= 0
                and not item_row.get("type")
                and not item_row.get("is_legacy_scrap_item")
            ):
                if self.purpose not in ["Receive from Customer", "Send to Subcontractor"]:
                    continue

            se_child = self.append("items")
            stock_uom = item_row.get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")
            se_child.s_warehouse = item_row.get("from_warehouse")
            se_child.t_warehouse = item_row.get("to_warehouse")
            se_child.item_code = item_row.get("item_code") or cstr(d)
            se_child.uom = item_row["uom"] if item_row.get("uom") else stock_uom
            se_child.stock_uom = stock_uom
            se_child.qty = child_qty if child_qty > 0 else 0
            se_child.allow_alternative_item = item_row.get("allow_alternative_item", 0)
            se_child.subcontracted_item = item_row.get("main_item_code")
            se_child.cost_center = item_row.get("cost_center") or get_default_cost_center(
                item_row, company=self.company
            )
            se_child.is_finished_item = item_row.get("is_finished_item", 0)
            # se_child.is_scrap_item = item_row.get("is_scrap_item", 0)
            se_child.po_detail = item_row.get("po_detail")
            
            se_child.sco_rm_detail = item_row.get("sco_rm_detail")
            se_child.merge = item_row.get("merge")
            
            se_child.scio_detail = item_row.get("scio_detail")
            se_child.sample_quantity = item_row.get("sample_quantity", 0)
            se_child.type = item_row.get("type")
            se_child.is_legacy_scrap_item = 1 if item_row.get("type") == "Scrap" else 0

            se_child.bom_secondary_item = item_row.get("name") or item_row.get("bom_secondary_item")

            for field in [
                self.subcontract_data.rm_detail_field,
                "original_item",
                "expense_account",
                "description",
                "item_name",
                "serial_and_batch_bundle",
                "allow_zero_valuation_rate",
                "use_serial_batch_fields",
                "batch_no",
                "serial_no",
            ]:
                if item_row.get(field):
                    se_child.set(field, item_row.get(field))

            if se_child.s_warehouse is None:
                se_child.s_warehouse = self.from_warehouse
            if se_child.t_warehouse is None:
                se_child.t_warehouse = self.to_warehouse

            # in stock uom
            se_child.conversion_factor = flt(item_row.get("conversion_factor")) or 1
            se_child.transfer_qty = flt(
                item_row["qty"] * se_child.conversion_factor, se_child.precision("qty")
            )

            se_child.bom_no = bom_no  # to be assigned for finished item
            se_child.job_card_item = item_row.get("job_card_item") if self.get("job_card") else None
