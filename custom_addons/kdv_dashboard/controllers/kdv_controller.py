from odoo import http
from odoo.http import request
from datetime import date
from dateutil.relativedelta import relativedelta


class KDVDashboardController(http.Controller):

    @http.route('/kdv_dashboard/data', type='json', auth='user')
    def get_kdv_data(self, **kwargs):
        today = date.today()
        year_start = date(today.year, 1, 1)

        # Get monthly breakdown for current year + past months with data
        monthly_data = []

        # Go back to find earliest invoice
        earliest = request.env['account.move'].sudo().search(
            [('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])],
            order='invoice_date asc', limit=1
        )
        
        if earliest and earliest.invoice_date:
            start_date = date(earliest.invoice_date.year, earliest.invoice_date.month, 1)
        else:
            start_date = year_start

        # Generate months from start to current + 1
        current = start_date
        end_limit = today + relativedelta(months=1)
        
        while current <= end_limit:
            month_end = current + relativedelta(months=1, days=-1)
            data = self._get_tax_totals(current, month_end)
            data['month'] = current.strftime('%Y-%m')
            data['month_label'] = self._turkish_month(current.month) + ' ' + str(current.year)
            data['is_current'] = (current.month == today.month and current.year == today.year)
            monthly_data.append(data)
            current = current + relativedelta(months=1)

        # Current quarter totals
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        quarter_start = date(today.year, quarter_month, 1)
        quarter_end = quarter_start + relativedelta(months=3, days=-1)
        quarterly = self._get_tax_totals(quarter_start, quarter_end)

        # Yearly totals
        yearly = self._get_tax_totals(year_start, date(today.year, 12, 31))

        return {
            'monthly': monthly_data,
            'quarterly': quarterly,
            'yearly': yearly,
            'period_labels': {
                'quarter': f'Q{(today.month - 1) // 3 + 1} {today.year}',
                'year': str(today.year),
            }
        }

    def _get_tax_totals(self, date_from, date_to):
        domain_base = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', str(date_from)),
            ('invoice_date', '<=', str(date_to)),
        ]

        sales = request.env['account.move'].sudo().search(
            domain_base + [('move_type', 'in', ['out_invoice', 'out_refund'])]
        )
        sales_tax = sum(sales.mapped('amount_tax'))
        sales_untaxed = sum(sales.mapped('amount_untaxed'))

        purchases = request.env['account.move'].sudo().search(
            domain_base + [('move_type', 'in', ['in_invoice', 'in_refund'])]
        )
        purchase_tax = sum(purchases.mapped('amount_tax'))
        purchase_untaxed = sum(purchases.mapped('amount_untaxed'))

        net_kdv = sales_tax - purchase_tax

        return {
            'sales_tax': sales_tax,
            'sales_untaxed': sales_untaxed,
            'purchase_tax': purchase_tax,
            'purchase_untaxed': purchase_untaxed,
            'net_kdv': net_kdv,
        }

    def _turkish_month(self, month):
        months = {
            1: 'Ocak', 2: 'Subat', 3: 'Mart', 4: 'Nisan',
            5: 'Mayis', 6: 'Haziran', 7: 'Temmuz', 8: 'Agustos',
            9: 'Eylul', 10: 'Ekim', 11: 'Kasim', 12: 'Aralik'
        }
        return months.get(month, '')
