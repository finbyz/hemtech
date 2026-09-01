import frappe
from erpnext.stock.get_item_details import get_item_tax_template


def fetch_gst_treatment_from_item_group(doc, method=None):
    """Re-resolve gst_treatment via Item -> Item Group tax template
    for any row that fell back to 'Nil-Rated' (usually because it has
    no item_tax_template — happens on rows added via Update Items)."""
    for item in doc.items:
        if item.gst_treatment != "Nil-Rated":
            continue

        item_doc = frappe.get_cached_doc("Item", item.item_code)

        ctx = {
            "company": doc.company,
            "transaction_date": doc.get("transaction_date") or doc.get("posting_date"),
            "tax_category": doc.get("tax_category"),
            "item_tax_template": item.item_tax_template,
        }

        item_tax_template = get_item_tax_template(ctx, item_doc)
        if not item_tax_template:
            continue  # genuinely no template anywhere in the tree — leave as is

        gst_treatment = frappe.get_cached_value(
            "Item Tax Template", item_tax_template, "gst_treatment"
        )
        if gst_treatment:
            item.item_tax_template = item_tax_template
            item.gst_treatment = gst_treatment