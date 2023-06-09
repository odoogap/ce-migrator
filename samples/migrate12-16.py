import os
import odoolib
from cemigrate import DISABLED_MAIL_CONTEXT
from cemigrate import MigrateToolBase


class MigrateTool(MigrateToolBase):

    def transform_res_partner(self, vals, key_fields):
        vals['customer_rank'] = vals.get('customer', False) and 1 or 0
        vals['supplier_rank'] = vals.get('supplier', False) and 1 or 0
        vals.pop('customer', None)
        vals.pop('supplier', None)

        return vals, key_fields

    def post_res_users(self, users):
        """implies we import users first, partners second"""
        remote_rs = self.connection.get_model('res.users')
        remote_rs_p = self.connection.get_model('res.partner')
        for user in users:
            if not user:
                continue
            user_dict = remote_rs.search_read([('id', '=', user.x_res_users_id)], ['partner_id'])
            if user_dict:
                [user_dict] = user_dict
                user.partner_id.x_res_partner_id = user_dict['partner_id'][0]

                partner_dict = remote_rs_p.search_read([('id', '=', user_dict['partner_id'][0])], ['email'])
                if partner_dict:
                    [partner_dict] = partner_dict
                    user.email = partner_dict['email']

    def transform_hr_leave_allocation(self, vals, key_fields=False):
        vals['date_from'] = '2022-01-01'
        return vals, key_fields

    def post_leave_allocation(self, records):
        remote_rs = self.connection.get_model('hr.leave.allocation')
        for record in records:
            [rec_dict] = remote_rs.search_read([('id', '=', record.x_hr_leave_allocation_id)], ['state'])
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
                new_id = rs1.search([('x_mail_message_id', '=', vals['res_id'])])
                if new_id:
                    vals['res_id'] = new_id.id
                else:
                    vals = False
            else:
                vals = False
        return vals, key_fields

    def transform_account_move(self, vals, key_fields):
        vals['invoice_origin'] = vals.get('origin', '')
        vals.pop('origin', None)
        return vals, key_fields

    def ensure_old_id(self, model_name, new_model_name):
        # TODO: fix this. when model inherits from other we need to create x_model_id on the main model
        mm = model_name == 'res.users' and 'res.partner' or new_model_name
        super(MigrateTool, self).ensure_old_id(model_name, mm)


connection = odoolib.get_connection(
        hostname=os.environ.get('OLD_HOSTNAME', "localhost"),
        database=os.environ.get('OLD_DATABASE', "v12_odoo"),
        login=os.environ.get('OLD_LOGIN', "admin"),
        password=os.environ.get('OLD_PASSWORD', "admin"),
        port=int(os.environ.get('OLD_PORT', 443)),
        protocol=os.environ.get('OLD_PROTOCOL', "jsonrpcs")
)

mt = MigrateTool(env, connection, False)

# mt.print_diff('res.partner')

# base objects
mt.init_import_models('res.country')
mt.init_import_models('res.country.state')
mt.init_import_models('res.currency')

# # users partners
# # res.users now inherit from res.partner so this is a problem but we will accept it for this database
mt.init_import_models('res.users')
mt.init_import_models('res.partner')

mt.import_basic_types('res.partner', ['customer', 'supplier', 'is_company'])
mt.update_many2one_fields('res.partner', ['country_id', 'state_id', 'parent_id'])

# leads
mt.init_import_models('crm.lead.tag')
mt.init_import_models('crm.stage')
mt.import_basic_types('crm.lead', ['description'])
mt.init_import_models('crm.team')
mt.update_many2one_fields('crm.lead', ['user_id', 'country_id', 'stage_id', 'team_id', 'company_currency'])
mt.update_many2many_fields('crm.lead', ['tag_ids'])

mt.copy_chatter('crm.lead')

mt.init_import_models('hr.employee')
mt.import_basic_types('hr.employee')
mt.update_many2one_fields('hr.employee', ['user_id'])
mt.init_import_models('hr.leave.type')
mt.import_basic_types('hr.leave.type')
mt.init_import_models('res.company')
mt.import_basic_types('res.company')
mt.init_import_models('hr.leave.allocation')
mt.init_import_models('hr.leave')

mt.init_import_models('account.payment.term')
mt.init_import_models('account.fiscal.position')


# # TODO: invoices
# # set ir_config 'sequence.mixin.constraint_start_date', '1970-01-01'
# mt.print_diff('account.invoice')
# mt.init_import_models('account.invoice')
# mt.import_basic_types('account.invoice', ['partner_id', 'date_invoice', 'user_id', 'fiscal_position_id', 'type', 'reference', 'number'])
# # TODO: implement
# mt.update_one2many_fields('account.invoice', 'line_ids')
