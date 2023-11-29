# Copyright (c) 2023, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
  columns = [
    {"label": _("Reference Doctype"), "fieldname": "reference_doctype", "width": 120,'hidden':1},
    {"label": _("Reference Docname"), "fieldname": "reference_docname", "fieldtype": "Dynamic Link", "options":"reference_doctype","width": 120},
    {"label": _("Item Code"), "fieldname": "package_item", "fieldtype": "Link", "options": "Item", "width": 310},
    {"label": _("Batch No"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 120},
    {"label": _("Consumed Quantity"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 150},
    {"label": _("Actual Quantity"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 150},
    {"label": _("Difference Quantity"), "fieldname": "diff_qty", "fieldtype": "Float", "width": 150},
    {"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 150,"hidden":1},
    {"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link","options":"voucher_type", "width": 150}
  ]
  return columns


def get_data(filters):

    condition = ""
    condition_sle = ""
    if filters.get("batch_no"):
        condition += f"AND pb.batch_no = '{filters.get('batch_no')}'"
        condition_sle += f"AND sle.batch_no = '{filters.get('batch_no')}'"

    # Query for Package Box and Consumption
    data_for_package = frappe.db.sql(f"""
        SELECT pb.item_code, pb.batch_no, SUM(pc.consumed_qty) as qty, pc.reference_docname,pc.reference_doctype
        FROM `tabPackage Box` pb
        INNER JOIN `tabPackage Consumption` pc ON pb.name = pc.parent
        WHERE date(pc.posting_date) BETWEEN "{filters.get('from_date')}" AND "{filters.get('to_date')}" AND pb.item_code = "{filters.get('item_code')}" AND pb.company = "{filters.get('company')}" {condition}
        GROUP BY pb.item_code, pb.batch_no, pc.reference_docname,pc.reference_doctype
    """, as_dict=True)
    pgk_dict = {}
    for row in data_for_package:
        pgk_dict.update({(row.reference_docname, row.item_code, row.batch_no): row})

    # Query for Stock Entry and Ledger Entry
    data_for_stock_entry = frappe.db.sql(f"""
        SELECT se.reference_docname, SUM(sle.actual_qty) AS actual_qty, sle.item_code as item_code, sle.batch_no as batch_no, sle.voucher_no AS v_no,sle.voucher_type as voucher_type
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabStock Entry` se ON se.name = sle.voucher_no
        WHERE sle.actual_qty < 0 AND date(sle.posting_date) BETWEEN "{filters.get('from_date')}" AND "{filters.get('to_date')}" AND sle.item_code = "{filters.get('item_code')}" AND sle.company = "{filters.get('company')}"{condition_sle}
        GROUP BY v_no, sle.item_code, sle.batch_no,se.reference_docname,se.reference_doctype,sle.voucher_type
    """, as_dict=True)

    final_data = []
    for row in data_for_stock_entry:
        pkg_data = pgk_dict.get((row.get('reference_docname'), row.get('item_code'), row.get('batch_no')))
        if not pkg_data:
           pkg_data = pgk_dict.get((row.get('v_no'), row.get('item_code'), row.get('batch_no')))
        if pkg_data:
            final_data.append({
                'reference_doctype':pkg_data['reference_doctype'],
                'reference_docname':pkg_data['reference_docname'],
                'package_item': pkg_data['item_code'],
                'batch_no': pkg_data['batch_no'],
                'consumed_qty': pkg_data['qty'],
                'actual_qty': row['actual_qty'],
                "diff_qty": pkg_data['qty'] + row['actual_qty'],
                'voucher_type':row['voucher_type'],
                'voucher_no': row['v_no']
            })

    return final_data




