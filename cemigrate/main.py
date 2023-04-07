from .migrate_tool import MigrateTool
from .migrate_tool import DISABLED_MAIL_CONTEXT


class MigrateToolInherit(MigrateTool):

    def transform_res_partner(self, vals, key_fields):
        vals['customer_rank'] = vals.get('customer', False) and 1 or 0
        vals['supplier_rank'] = vals.get('supplier', False) and 1 or 0
        vals.pop('customer', None)
        vals.pop('supplier', None)
        return vals, key_fields

    def post_res_users(self, users):
        remote_rs = self.connection.get_model('res.users')
        for user in users:
            if not user:
                continue
            self.iprint(user)
            [user_dict] = remote_rs.search_read([('id', '=', user.old_id)], ['partner_id'])
            user.partner_id.old_id = user_dict['partner_id'][0]

    def transform_hr_leave_allocation(self, vals, key_fields=False):
        vals['date_from'] = '2022-01-01'
        return vals, key_fields

    def post_leave_allocation(self, records):
        remote_rs = self.connection.get_model('hr.leave.allocation')
        for record in records:
            [rec_dict] = remote_rs.search_read([('id', '=', record.old_id)], ['state'])
            if record.state == 'draft':
                if rec_dict['state'] == 'confirm':
                    record.action_confirm()
                elif rec_dict['state'] == 'validate':
                    record.action_confirm()
                    record.action_validate()

    def transform_hr_leave(self, vals, key_fields=False):
        vals['date_from'] = vals['request_date_from']
        vals['date_to'] = vals['request_date_to']
        if vals['request_date_from'] == vals['request_date_to']:
            vals['number_of_days'] = 1
        return vals, key_fields

    def post_hr_leave(self, records):
        for record in records:
            if record.state == 'draft':
                record.action_approve()
            if record.state == 'confirm':
                record.action_validate()

    def transform_account_invoice(self, vals, key_fields):
        vals['invoice_date'] = vals.get('date_invoice', False)
        vals['invoice_date_due'] = vals.get('date_due', False)
        vals['ref'] = vals.get('reference', False)
        map_type = {
            'out_invoice': 'out_invoice',
            'in_invoice': 'in_invoice',
            'out_refund': 'out_refund',
            'in_refund': 'in_refund',
        }
        vals['move_type'] = map_type[vals['type']]
        vals.pop('type', None)
        vals.pop('date_invoice', None)
        vals.pop('date_due', None)
        vals.pop('reference', None)

        if key_fields:
            return vals, ['partner_id', 'invoice_date', 'user_id', 'move_type']
        else:
            return vals, key_fields

    def transform_mail_message(self, vals, key_fields):
        if vals.get('model', False):
            new_model_name = self._get_field_info_dict(vals['model'])['new_model_name']
            rs1 = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
            vals['model'] = new_model_name
            if vals.get('res_id', False):
                new_id = rs1.search([('old_id', '=', vals['res_id'])])
                if new_id:
                    vals['res_id'] = new_id.id
                else:
                    vals = False
            else:
                vals = False
        return vals, key_fields
