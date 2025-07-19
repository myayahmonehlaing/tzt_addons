# controllers/main.py
from odoo import http
from odoo.http import request
import io
import xlsxwriter


class ConsignmentReportController(http.Controller):

    @http.route('/web/binary/download_consignment_excel', type='http', auth="user")
    def download_excel(self, wizard_id):
        wizard = request.env['consignment.report.wizard'].browse(int(wizard_id))

        data = wizard._prepare_report_data()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Consignment Report')

        customers = list(next(iter(data['data'].values())).keys())
        sheet.write(0, 0, "Product")
        for col, customer in enumerate(customers, start=1):
            sheet.write(0, col, customer)

        for row, (product, values) in enumerate(data['data'].items(), start=1):
            sheet.write(row, 0, product)
            for col, customer in enumerate(customers, start=1):
                sheet.write(row, col, values.get(customer, 0))

        workbook.close()
        output.seek(0)

        filename = 'Consignment_Report.xlsx'
        return request.make_response(output.read(),
                                     headers=[
                                         ('Content-Type',
                                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                         ('Content-Disposition', f'attachment; filename={filename}')
                                     ])
