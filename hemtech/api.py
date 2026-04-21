# -*- coding: utf-8 -*-
# Copyright (c) 2018, Finbyz Tech Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, db
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact
from frappe.model.mapper import get_mapped_doc
from frappe.utils.data import flt
import datetime
from frappe.utils import (
	add_days,
	today,
)

@frappe.whitelist()
def mn_validate(self, method):
	self.flags.is_new_doc = self.is_new()

@frappe.whitelist()
def mn_onload(self, method):
	"""Load address and contacts in `__onload`"""
	load_address_and_contact(self)

@frappe.whitelist()
def mn_on_trash(self, method):
	delete_contact_and_address('Manufacturer', self.name)

def customer_group_filter(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select customer_name, customer_group from `tabCustomer` where customer_group = '%s'""" % filters.get('customer_group'))

@frappe.whitelist()
def get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	if not party:
		return {}

	if not db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))

	return _get_party_details(party, party_type, ignore_permissions)

def _get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	out = frappe._dict({
		party_type.lower(): party
	})

	party = out[party_type.lower()]

	if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
		frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)
	
	set_address_details(out, party, party_type)
	set_contact_details(out, party, party_type)
	set_other_values(out, party, party_type)

	if party_type == 'Lead':
		out.organisation = party.company_name
	elif party_type == 'Customer':
		out.organisation = party.customer_name

	return out

def set_address_details(out, party, party_type):
	billing_address_field = "customer_address" if party_type == "Lead" \
		else party_type.lower() + "_address"
	out[billing_address_field] = get_default_address(party_type, party.name)
	
	out.address_display = get_address_display(out[billing_address_field])

def set_contact_details(out, party, party_type):
	out.contact_person = get_default_contact(party_type, party.name)

	if not out.contact_person:
		out.update({
			"contact_person": None,
			"contact_display": None,
			"contact_email": None,
			"contact_mobile": None,
			"contact_phone": None,
			"contact_designation": None,
			"contact_department": None
		})
	else:
		out.update(get_contact_details(out.contact_person))

def set_other_values(out, party, party_type):
	# copy
	if party_type=="Customer":
		to_copy = ["customer_name", "customer_group", "territory", "language"]
	else:
		to_copy = ["supplier_name", "supplier_type", "language"]
	for f in to_copy:
		out[f] = party.get(f)


def check_sub_string(string, sub_string): 
	"""Function to check if string has sub string"""

	return not string.find(sub_string) == -1

from erpnext.accounts.utils import get_fiscal_year

@frappe.whitelist()
def get_fiscal(date):
	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	return fiscal if fiscal else fy.split("-")[0][2:] + fy.split("-")[1][2:]

def naming_series_name(name, fiscal = None, company_series = None):
	from datetime import date
	if fiscal == None:
		fiscal = ''

	if company_series:
		name = name.replace('company_series', str(company_series))
	
	name = name.replace('YYYY', str(date.today().year))
	name = name.replace('YY', str(date.today().year)[2:])
	name = name.replace('MM', '%02d' % date.today().month)
	name = name.replace('DD', '%02d' % date.today().day)
	name = name.replace('fiscal', str(fiscal))
	name = name.replace('#', '')
	name = name.replace('.', '')

	return name

# all whitelist functions bellow

@frappe.whitelist()
def check_counter_series(name, company_series = None, date = None):
	"""Function to get series value for naming series"""
	
	if not date:
		date = datetime.date.today()
	
	fiscal = get_fiscal(date)
	# renaming the name for naming series
	name = naming_series_name(name, fiscal, company_series)
	name = name.replace('.', '')
	# frappe.throw(name)
	# Checking the current series value
	check = frappe.db.get_value('Series', name, 'current', order_by="name")
	
	# returning the incremented value of check for series value
	if check == 0:
		return 1
	elif check == None:
		# if no current value is found for naming series inserting that naming series with current value 0
		frappe.db.sql("insert into tabSeries (name, current) values ('{}', 0)".format(name))
		return 1
	else:
		return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1

@frappe.whitelist()
def before_naming(self, method = None):
	"""Function for naming the name of naming series"""

	# if from is not ammended and series_value is greater than zero then 
	if not self.amended_from:
		if self.series_value:
			if self.series_value > 0:
				
				# renaming the name for naming series
				name = naming_series_name(self.naming_series, self.company_series)
				name = name.replace('.', '')
				# Checking the current series value
				check = frappe.db.get_value('Series', name, 'current', order_by="name")
				
				# if no current value is found inserting 0 for current value for this naming series
				if check == 0:
					pass
				elif not check:
					frappe.db.sql("insert into tabSeries (name, current) values ('{}', 0)".format(name))
				
				# Updating the naming series decremented by 1 for current naming series
				frappe.db.sql("update `tabSeries` set current = {} where name = '{}'".format(int(self.series_value) - 1, name))

# def stock_reconciliation_validate(self,method):
# 	validate_batch_no_stock_reconciliaton(self)

# def validate_batch_no_stock_reconciliaton(self):
# 	for item in self.items:
# 		if frappe.db.get_value("Item",item.item_code,"has_batch_no"):
# 			frappe.throw("In Items Row: {} and Item: {}, For Batch wise items do Material Issue and Material Receipt instead of Stock Reconciliation to avoid mismatch in Packages".format(frappe.bold(item.idx),frappe.bold(item.item_code)))

@frappe.whitelist()
def change_email_queue_status():
	# from frappe.email.doctype.email_queue.email_queue import retry_sending
	# from frappe.email.queue import send_one

	eqs = frappe.db.sql("select name from `tabEmail Queue` where status = 'Error' and  creation > now() - interval 6 hour")
	
	if eqs:
		for d in eqs:
			# retry_sending(d.name)
			# send_one(d.name, now=True)
			doc = frappe.get_doc("Email Queue", d.name)
			doc.status = "Not Sent"
			doc.save(ignore_permissions=True)
			#send_one(doc.name, now=True)
		else:
			frappe.db.commit()

def delete_email_queue():
	frappe.enqueue("hemtech.api.delete_email_queue_job", queue='long')

def delete_email_queue_job():
	from frappe.utils import add_days,today

	frappe.db.sql(f"""DELETE FROM `tabEmail Queue` where modified < '{add_days(today(), -7)}'""")
	frappe.db.sql(f"""DELETE FROM `tabEmail Queue Recipient` where modified < '{add_days(today(), -7)}'""")


@frappe.whitelist()
def make_material_transfer(source_name, target_doc=None):
   

    def update_item(src_row, tgt_row, src_parent):
        qty = flt(src_row.stock_qty) - flt(src_row.ordered_qty)
        if qty < 0:
            qty = 0

        tgt_row.item_code = src_row.item_code
        tgt_row.item_name = src_row.item_name
        tgt_row.description = src_row.description
        tgt_row.uom = src_row.uom
        tgt_row.qty = qty
        tgt_row.basic_rate = src_row.rate
        # tgt_row.merge = src_row.merge
        # tgt_row.grade = src_row.grade
        # source warehouse from MR item
        tgt_row.s_warehouse = src_row.from_warehouse or src_row.warehouse
        tgt_row.t_warehouse = src_parent.set_warehouse

    def set_missing_values(src, tgt):
  
        tgt.company = src.company
        tgt.posting_date = frappe.utils.nowdate()
        tgt.material_request = src.name
        tgt.s_warehouse = src.set_from_warehouse
        tgt.t_warehouse = src.set_warehouse


    doc = get_mapped_doc(
        "Material Request",
        source_name,
        {
            "Material Request": {
                "doctype": "Material Transfer",        
                "field_map": {
                    # map fields if names differ; example below
                    # "set_from_warehouse": "from_warehouse",
                    # "set_warehouse": "to_warehouse",
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"job_card_item": "job_card_item",
                },
                "validation": {
                    "docstatus": ["=", 1],
                    "material_request_type": ["=", "Material Transfer"],
                },
            },
            "Material Request Item": {
                "doctype": "Material Transfer Item",   # << your custom child doctype
                "field_map": {
                    # examples if your target fields differ
                    # "uom": "stock_uom",
                },
                "postprocess": update_item,
                "condition": lambda d: flt(d.stock_qty) > flt(d.ordered_qty),
                # or simply: lambda d: flt(d.qty) > 0
            },
        },
        target_doc,
        set_missing_values,
    )

    return doc
