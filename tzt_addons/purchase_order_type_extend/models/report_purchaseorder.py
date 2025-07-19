from odoo import models

class PurchaseOrderReport(models.AbstractModel):
    _name = 'report.purchase.report_purchaseorder_document'
    _description = 'Purchase Order Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
            'doc': docs[0] if docs else None,  # Avoid KeyError
        }
