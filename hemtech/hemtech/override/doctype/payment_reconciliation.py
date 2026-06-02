from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation as _PaymentReconciliation
from frappe.utils import flt, fmt_money, get_link_to_form, getdate, nowdate, today
import frappe
from erpnext.accounts.utils import create_gain_loss_journal
import erpnext
from frappe.utils import flt, today
from frappe import _

class PaymentReconciliation(_PaymentReconciliation):
	def get_allocated_entry(self, pay, inv, allocated_amount):
		res = frappe._dict(
			{
				"reference_type": pay.get("reference_type"),
				"reference_name": pay.get("reference_name"),
				"posting_date": pay.get("posting_date"), # Finbyz Changes
				"reference_row": pay.get("reference_row"),
				"invoice_type": inv.get("invoice_type"),
				"invoice_number": inv.get("invoice_number"),
				"unreconciled_amount": pay.get("unreconciled_amount"),
				"amount": pay.get("amount"),
				"allocated_amount": allocated_amount,
				"difference_amount": pay.get("difference_amount"),
				"currency": inv.get("currency"),
				"cost_center": pay.get("cost_center"),
			}
		)

		res = self.update_dimension_values_in_allocated_entries(res)
		return res

	def get_payment_details(self, row, dr_or_cr):
		try:
			posting_date = frappe.db.get_value(row.get("reference_type"), row.get("reference_name"), "posting_date")
		except Exception as e:
			posting_date = None
		
		payment_details = frappe._dict(
			{
				"voucher_type": row.get("reference_type"),
				"voucher_no": row.get("reference_name"),
				"posting_date" : posting_date, # Finbyz Changes
				"voucher_detail_no": row.get("reference_row"),
				"against_voucher_type": row.get("invoice_type"),
				"against_voucher": row.get("invoice_number"),
				"account": self.receivable_payable_account,
				"exchange_rate": row.get("exchange_rate"),
				"party_type": self.party_type,
				"party": self.party,
				"is_advance": row.get("is_advance"),
				"dr_or_cr": dr_or_cr,
				"unreconciled_amount": flt(row.get("unreconciled_amount")),
				"unadjusted_amount": flt(row.get("amount")),
				"allocated_amount": flt(row.get("allocated_amount")),
				"difference_amount": flt(row.get("difference_amount")),
				"difference_account": row.get("difference_account"),
				"difference_posting_date": row.get("gain_loss_posting_date"),
				"cost_center": row.get("cost_center"),
			}
		)

		for x in self.dimensions:
			if row.get(x.fieldname):
				payment_details[x.fieldname] = row.get(x.fieldname)

		return payment_details
	def reconcile_dr_cr_note(dr_cr_notes, company, active_dimensions=None):
		for inv in dr_cr_notes:
			voucher_type = "Credit Note" if inv.voucher_type == "Sales Invoice" else "Debit Note"

			reconcile_dr_or_cr = (
				"debit_in_account_currency"
				if inv.dr_or_cr == "credit_in_account_currency"
				else "credit_in_account_currency"
			)

			company_currency = erpnext.get_company_currency(company)

			jv = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"voucher_type": voucher_type,
					"posting_date": inv.get('posting_date') or today(), # Finbyz Changes
					"company": company,
					"multi_currency": 1 if inv.currency != company_currency else 0,
					"accounts": [
						{
							"account": inv.account,
							"party": inv.party,
							"party_type": inv.party_type,
							inv.dr_or_cr: abs(inv.allocated_amount),
							"reference_type": inv.against_voucher_type,
							"reference_name": inv.against_voucher,
							"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
							"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} against {inv.against_voucher}",
							"exchange_rate": inv.exchange_rate,
						},
						{
							"account": inv.account,
							"party": inv.party,
							"party_type": inv.party_type,
							reconcile_dr_or_cr: (
								abs(inv.allocated_amount)
								if abs(inv.unadjusted_amount) > abs(inv.allocated_amount)
								else abs(inv.unadjusted_amount)
							),
							"reference_type": inv.voucher_type,
							"reference_name": inv.voucher_no,
							"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
							"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} from {inv.voucher_no}",
							"exchange_rate": inv.exchange_rate,
						},
					],
				}
			)

			# Credit Note(JE) will inherit the same dimension values as payment
			dimensions_dict = frappe._dict()
			if active_dimensions:
				for dim in active_dimensions:
					dimensions_dict[dim.fieldname] = inv.get(dim.fieldname)

			jv.accounts[0].update(dimensions_dict)
			jv.accounts[1].update(dimensions_dict)

			jv.flags.ignore_mandatory = True
			jv.flags.skip_remarks_creation = True
			jv.flags.ignore_exchange_rate = True
			jv.is_system_generated = True
			jv.remark = None
			jv.submit()

			if inv.difference_amount != 0:
				# make gain/loss journal
				if inv.party_type == "Customer":
					dr_or_cr = "credit" if inv.difference_amount < 0 else "debit"
				else:
					dr_or_cr = "debit" if inv.difference_amount < 0 else "credit"

				reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

				create_gain_loss_journal(
					company,
					inv.get('posting_date') or today(),
					inv.party_type,
					inv.party,
					inv.account,
					inv.difference_account,
					inv.difference_amount,
					dr_or_cr,
					reverse_dr_or_cr,
					inv.voucher_type,
					inv.voucher_no,
					None,
					inv.against_voucher_type,
					inv.against_voucher,
					None,
					inv.cost_center,
					dimensions_dict,
				)


def reconcile_dr_cr_note(dr_cr_notes, company, active_dimensions=None):
	"""
	Override of ERPNext's reconcile_dr_cr_note to use the return invoice's
	actual posting date instead of today() for the created Journal Entry.
	"""
	from erpnext.accounts.utils import create_gain_loss_journal
	from frappe.utils import fmt_money

	for inv in dr_cr_notes:
		if (
			abs(frappe.db.get_value(inv.voucher_type, inv.voucher_no, "outstanding_amount"))
			< inv.allocated_amount
		):
			frappe.throw(
				_("{0} has been modified after you pulled it. Please pull it again.").format(inv.voucher_type)
			)

		voucher_type = "Credit Note" if inv.voucher_type == "Sales Invoice" else "Debit Note"

		reconcile_dr_or_cr = (
			"debit_in_account_currency"
			if inv.dr_or_cr == "credit_in_account_currency"
			else "credit_in_account_currency"
		)

		company_currency = erpnext.get_company_currency(company)

		# Use the return invoice's actual posting date instead of today()
		posting_date = (
			inv.get("debit_or_credit_note_posting_date")
			or frappe.db.get_value(inv.voucher_type, inv.voucher_no, "posting_date")
			or today()
		)

		jv = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": voucher_type,
				"posting_date": posting_date,
				"company": company,
				"multi_currency": 1 if inv.currency != company_currency else 0,
				"accounts": [
					{
						"account": inv.account,
						"party": inv.party,
						"party_type": inv.party_type,
						inv.dr_or_cr: abs(inv.allocated_amount),
						"reference_type": inv.against_voucher_type,
						"reference_name": inv.against_voucher,
						"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
						"exchange_rate": inv.exchange_rate,
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} against {inv.against_voucher}",
					},
					{
						"account": inv.account,
						"party": inv.party,
						"party_type": inv.party_type,
						reconcile_dr_or_cr: (
							abs(inv.allocated_amount)
							if abs(inv.unadjusted_amount) > abs(inv.allocated_amount)
							else abs(inv.unadjusted_amount)
						),
						"reference_type": inv.voucher_type,
						"reference_name": inv.voucher_no,
						"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
						"exchange_rate": inv.exchange_rate,
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} from {inv.voucher_no}",
					},
				],
			}
		)

		# Credit Note(JE) will inherit the same dimension values as payment
		dimensions_dict = frappe._dict()
		if active_dimensions:
			for dim in active_dimensions:
				dimensions_dict[dim.fieldname] = inv.get(dim.fieldname)

		jv.accounts[0].update(dimensions_dict)
		jv.accounts[1].update(dimensions_dict)

		jv.flags.ignore_mandatory = True
		jv.flags.ignore_exchange_rate = True
		jv.remark = None
		jv.flags.skip_remarks_creation = True
		jv.is_system_generated = True
		jv.submit()

		if inv.difference_amount != 0:
			# make gain/loss journal
			if inv.party_type == "Customer":
				dr_or_cr = "credit" if inv.difference_amount < 0 else "debit"
			else:
				dr_or_cr = "debit" if inv.difference_amount < 0 else "credit"

			reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

			create_gain_loss_journal(
				company,
				inv.difference_posting_date,
				inv.party_type,
				inv.party,
				inv.account,
				inv.difference_account,
				inv.difference_amount,
				dr_or_cr,
				reverse_dr_or_cr,
				inv.voucher_type,
				inv.voucher_no,
				None,
				inv.against_voucher_type,
				inv.against_voucher,
				None,
				inv.cost_center,
				dimensions_dict,
			)
