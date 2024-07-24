from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder as _WorkOrder
from frappe.utils import flt
class WorkOrder(_WorkOrder):
	def get_status(self, status=None):
		"""Return the status based on stock entries against this work order"""
		if not status:
			status = self.status

		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if status != "Stopped":
				status = "Not Started"
				# Finbyz Changes Start
				#if flt(self.material_transferred_for_manufacturing) > 0:
				if flt(self.produced_qty) < flt(self.qty):
					status = "In Process"
				# Finbyz Changes End

				total_qty = flt(self.produced_qty) + flt(self.process_loss_qty)
				if flt(total_qty) >= flt(self.qty):
					status = "Completed"
		else:
			status = "Cancelled"

		if (
			self.skip_transfer
			and self.produced_qty
			and self.qty > (flt(self.produced_qty) + flt(self.process_loss_qty))
		):
			status = "In Process"

		return status