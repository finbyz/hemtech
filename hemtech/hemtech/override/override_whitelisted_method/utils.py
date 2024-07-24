import frappe
import json
import erpnext
from frappe.utils import flt
from erpnext.stock.utils import get_valuation_method
from erpnext.stock.utils import _get_fifo_lifo_rate
from erpnext.stock.utils import get_avg_purchase_rate

@frappe.whitelist()
def get_incoming_rate(args, raise_error_if_no_rate=True):
	"""Get Incoming Rate based on valuation method"""
	from erpnext.stock.stock_ledger import (
		get_batch_incoming_rate,
		get_previous_sle,
		get_valuation_rate,
	)

	if isinstance(args, str):
		args = json.loads(args)

	voucher_no = args.get("voucher_no") or args.get("name")

	in_rate = None
	if (args.get("serial_no") or "").strip():
		in_rate = get_avg_purchase_rate(args.get("serial_no"))
	elif args.get("batch_no") and frappe.db.get_value(
		"Batch", args.get("batch_no"), "use_batchwise_valuation", cache=True
	):
		in_rate = get_batch_incoming_rate(
			item_code=args.get("item_code"),
			warehouse=args.get("warehouse"),
			batch_no=args.get("batch_no"),
			posting_date=args.get("posting_date"),
			posting_time=args.get("posting_time"),
		)
	else:
		valuation_method = get_valuation_method(args.get("item_code"))
		previous_sle = get_previous_sle(args)
		if valuation_method in ("FIFO", "LIFO"):
			if previous_sle:
				previous_stock_queue = json.loads(previous_sle.get("stock_queue", "[]") or "[]")
				in_rate = (
					_get_fifo_lifo_rate(previous_stock_queue, args.get("qty") or 0, valuation_method)
					if previous_stock_queue
					else 0
				)
		elif valuation_method == "Moving Average":
			in_rate = previous_sle.get("valuation_rate") or 0

	# if in_rate is None:
	if (in_rate is None or in_rate == 0): # ERPPNext Issue there is no batch valuation so it is getting rate as 0 which does not satisfy condition and return rate as 0 # Finbyz Changes
		in_rate = get_valuation_rate(
			args.get("item_code"),
			args.get("warehouse"),
			args.get("voucher_type"),
			voucher_no,
			args.get("allow_zero_valuation"),
			currency=erpnext.get_company_currency(args.get("company")),
			company=args.get("company"),
			raise_error_if_no_rate=raise_error_if_no_rate,
			batch_no=args.get("batch_no"),
		)

	return flt(in_rate)
