import frappe
from frappe.utils.pdf import get_pdf
from frappe import _

def send_qc_notification(doc, method):
    customer_doc = frappe.get_doc("Customer", doc.customer)
    frappe.log_error(f"Customer: {customer_doc.name}, Send QC Notification: {customer_doc.send_qc_notification}")
    if not customer_doc.send_qc_notification:
        return

    if not doc.contact_email:
        return
    frappe.log_error(f"Preparing QC Notification for Delivery Note {doc.name} to be sent to {doc.contact_email}")
    attachments = []

    for item in doc.items:
        if not item.quality_inspection:
            continue
        html = frappe.get_print(
            "Quality Inspection",
            item.quality_inspection
        )

        pdf = get_pdf(html)

        attachments.append({
            "fname": f"{item.quality_inspection}.pdf",
            "fcontent": pdf
        })
    frappe.log_error(f"Total {len(attachments)} QC Reports attached for Delivery Note {doc.name}")
    if attachments:
        frappe.sendmail(
            recipients=[email.strip() for email in doc.contact_email.split(",")],
            subject=f"Quality Inspection Report - {doc.name}",
            message=f"""
                Dear Customer,<br><br>
                Please find attached Quality Inspection Report for Delivery Note <b>{doc.name}</b>.<br><br>
                Regards
            """,
            attachments=attachments
        )
        frappe.log_error(f"QC Notification sent to {doc.contact_email} for Delivery Note {doc.name}")
        
