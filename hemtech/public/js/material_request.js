frappe.ui.form.on('Material Request', {
    refresh(frm) {
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.status !== 'Stopped' &&
            frm.doc.material_request_type === 'Material Transfer'
        ) {
            
            frm.remove_custom_button("Material Transfer", "Create")
            frm.add_custom_button(
                "<p>Material Transfer</p>",
                () => { 
                     frappe.model.open_mapped_doc({
                        method: "hemtech.api.make_material_transfer", // << change app path
                        frm: frm
                });
                },
                "Create"
            )
        }
    }
});
