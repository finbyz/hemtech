import json
import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def make_quality_inspections(
	company: str, doctype: str, docname: str, items: str | list, inspection_type: str
):
	if isinstance(items, str):
		items = json.loads(items)

	inspections = []
	for item in items:
		if flt(item.get("sample_size")) > flt(item.get("qty")):
			frappe.throw(
				_(
					"{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})"
				).format(
					item_name=item.get("item_name"),
					sample_size=item.get("sample_size"),
					accepted_quantity=item.get("qty"),
				)
			)

		quality_inspection = frappe.get_doc(
			{
				"company": company,
				"doctype": "Quality Inspection",
				"inspection_type": inspection_type,
				"inspected_by": frappe.session.user,
				"reference_type": doctype,
				"reference_name": docname,
				"item_code": item.get("item_code"),
				"description": item.get("description"),
				"sample_size": flt(item.get("sample_size")),
				"item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
				"batch_no": item.get("batch_no"),
				"merge": item.get("merge"),
				"": item.get("child_row_reference"),
			}
		)
		quality_inspection.save()
		inspections.append(quality_inspection.name)

	return inspections
