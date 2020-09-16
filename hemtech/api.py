# -*- coding: utf-8 -*-
# Copyright (c) 2018, Finbyz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, db
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact

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

def naming_series_name(name, company_series = None):
	from datetime import date
	fiscal = get_fiscal(date.today())

	if company_series:
		name = name.replace('company_series', str(company_series))
	
	name = name.replace('YYYY', str(date.today().year))
	name = name.replace('YY', str(date.today().year)[2:])
	name = name.replace('MM', '%02d' % date.today().month)
	name = name.replace('fiscal', str(fiscal))
	name = name.replace('#', '')
	name = name.replace('.', '')

	return name

# all whitelist functions bellow

@frappe.whitelist()
def check_counter_series(name, company_series = None):
	"""Function to get series value for naming series"""
	
	# renaming the name for naming series
	name = naming_series_name(name, company_series)
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

def fiscal_before_save(self,method):
	start_date = str(self.year_start_date)
	end_date = str(self.year_end_date)

	fiscal = start_date.split("-")[0][2:] + end_date.split("-")[0][2:]
	self.fiscal = fiscal
