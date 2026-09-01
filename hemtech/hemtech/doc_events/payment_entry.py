import frappe
from frappe import _
from frappe.utils import flt


def validate(self, method):
    if self.payment_type == "Pay":
        if self.references:
            outstanding = sum([flt(row.outstanding_amount) for row in self.references])
            if  self.paid_amount > outstanding:
                frappe.throw(_("Paid amount is more than outstanding amount"))
