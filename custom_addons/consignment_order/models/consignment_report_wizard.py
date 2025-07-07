from odoo import models, fields, api
import io
import xlsxwriter
import base64


class ConsignmentReportWizard(models.TransientModel):
    _name = 'consignment.report.wizard'
    _description = 'Consignment Report Wizard'

    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )

    def _get_data(self):
        """
        Collects remaining quantities of consigned products per customer up to a given date.
        Returns a dictionary with:
            - date_to: string
            - data: {product_name: {customer_name: qty}}
            - customers: sorted list of customer names
            - products: sorted list of product names
        """
        orders = self.env['consignment.order'].search([
            ('state', '=', 'confirmed'),
            ('date', '<=', self.date_to),
        ])

        data = {}
        customer_names = set()
        product_names = set()

        for order in orders:
            customer = order.customer_id.name or 'Unknown Customer'
            for line in order.order_line:
                product = line.product_id.name or 'Unknown Product'
                customer_names.add(customer)
                product_names.add(product)

                if product not in data:
                    data[product] = {}

                current_qty = data[product].get(customer, 0.0)
                data[product][customer] = current_qty + line.remaining_qty

        return {
            'date_to': str(self.date_to or ''),
            'data': data,
            'customers': sorted(customer_names),
            'products': sorted(product_names),
        }

    def action_print_pdf(self):
        """
        Return the consignment orders as docs for the QWeb PDF report
        """
        orders = self.env['consignment.order'].search([
            ('state', '=', 'confirmed'),
            ('date', '<=', self.date_to),
        ])
        return self.env.ref('consignment_order.action_consignment_report_pdf').report_action(orders)

    def action_print_excel(self):
        """
        Generates and downloads a pivot-style Excel file:
        Rows = Products, Columns = Customers, Values = Remaining Qty
        """
        result = self._get_data()
        data = result['data']
        customers = result['customers']
        products = result['products']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Consignment Report')

        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})

        # Header row: customer names
        row, col = 0, 1
        for customer in customers:
            sheet.write(row, col, customer, header_format)
            col += 1

        # Product rows and quantities
        row = 1
        for product in products:
            sheet.write(row, 0, product, header_format)
            col = 1
            for customer in customers:
                qty = data.get(product, {}).get(customer, 0.0)
                sheet.write(row, col, qty)
                col += 1
            row += 1

        workbook.close()
        output.seek(0)
        encoded_file = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'Consignment_Report_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': encoded_file,
            'res_model': 'consignment.report.wizard',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_show_pivot(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consignment Pivot',
            'res_model': 'consignment.order.line',
            'view_mode': 'pivot',
            'view_id': self.env.ref('consignment_order.view_consignment_pivot').id,
            'target': 'current',
            'domain': [('order_id.date', '<=', self.date_to)] if self.date_to else [],
        }
