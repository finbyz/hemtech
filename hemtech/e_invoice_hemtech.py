import frappe
import frappe
import re
import jwt
from frappe import _
from frappe.utils.data import cstr, cint, flt
from erpnext.regional.india.e_invoice.utils import (read_json,get_transaction_details,get_item_list,sanitize_for_json,\
	validate_mandatory_fields,get_doc_details,get_overseas_address_details,get_return_doc_reference,\
	get_eway_bill_details,validate_totals,show_link_to_error_log,santize_einvoice_fields,safe_json_load,get_payment_details,\
	get_invoice_value_details)

from erpnext.regional.india.utils import get_place_of_supply
import json


def get_party_details(address_name, is_shipping_address=False):
	addr = frappe.get_doc('Address', address_name)

	validate_address_fields(addr, is_shipping_address)

	if addr.gst_state_number == 97:
		# according to einvoice standard
		addr.pincode = 999999

	party_address_details = frappe._dict(dict(
		legal_name=sanitize_for_json(addr.address_title),
		location=sanitize_for_json(addr.city),
		pincode=addr.pincode, gstin=addr.gstin,
		state_code=addr.gst_state_number,
		address_line1=sanitize_for_json(addr.address_line1),
		address_line2=sanitize_for_json(addr.address_line2)
	))
	#finbyz d to addr
	if addr.gstin:
		party_address_details.gstin = addr.gstin

	return party_address_details

def validate_address_fields(address, is_shipping_address):
	# finbyz change remove gstin
	if (not address.city
		or not address.pincode
		or not address.address_title
		or not address.address_line1
		or not address.gst_state_number):

		frappe.throw(
			msg=_('Address Lines, City, Pincode, GSTIN are mandatory for address {}. Please set them and try again.').format(address.name),
			title=_('Missing Address Fields')
		)


def make_einvoice(invoice):
	validate_mandatory_fields(invoice)

	schema = read_json('einv_template')

	transaction_details = get_transaction_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	invoice_value_details = get_invoice_value_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, invoice.doctype)
		if place_of_supply:
			place_of_supply = place_of_supply.split('-')[0]
		else:
			place_of_supply = invoice.billing_address_gstin[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	seller_details.update(dict(legal_name=invoice.company))
	buyer_details.update(dict(legal_name=invoice.customer_name or invoice.customer))
	
	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		if invoice.gst_category == 'Overseas':
			shipping_details = get_overseas_address_details(invoice.shipping_address_name)
		else:
			shipping_details = get_party_details(invoice.shipping_address_name) #finbyz
	
	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)
	
	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)

	if invoice.transporter and flt(invoice.distance) and not invoice.is_return:
		eway_bill_details = get_eway_bill_details(invoice)

	# not yet implemented
	dispatch_details = period_details = export_details = frappe._dict({})

	einvoice = schema.format(
		transaction_details=transaction_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, invoice_value_details=invoice_value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)
	
	try:
		einvoice = safe_json_load(einvoice)
		einvoice = santize_einvoice_fields(einvoice)
	except Exception:
		show_link_to_error_log(invoice, einvoice)

	validate_totals(einvoice)

	return einvoice