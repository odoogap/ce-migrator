{
    'account.fiscal.position': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'account.fiscal.position'
    },
    'account.invoice': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['id', 'display_type'],
        'new_model_name': 'account.move'},
    'account.move.line': {
        'create': True,
        'include_archived': False,
        'domain': [('display_type', 'in', ('product', 'line_section', 'line_note'))],
        'key_fields': [
            'id',
            'name',
            'move_name',
            'account_id',
            'date',
            'move_id',
            'product_id',
            'product_uom_id',
            'quantity',
            'date_maturity',
            'price_unit',
            'discount'],
        'new_model_name': 'account.move.line'
    },
    'account.payment.term': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name', 'note'],
        'new_model_name': 'account.payment.term'},
    'crm.lead': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'crm.lead'
    },
    'crm.lead.tag': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'crm.tag'
    },
    'crm.stage': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'crm.stage'
    },
    'crm.team': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name', 'alias_name'],
        'new_model_name': 'crm.team'
    },
    'hr.employee': {
        'create': True,
        'extra_args': {},
        'include_archived': True,
        'key_fields': ['name'],
        'new_model_name': 'hr.employee'},
    'hr.leave': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': [
            'holiday_status_id',
            'employee_id',
            'request_date_from',
            'request_date_to',
            'request_unit_half',
            'holiday_type'
        ],
        'new_model_name': 'hr.leave'
    },
    'hr.leave.allocation': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': [
            'name',
            'holiday_status_id',
            'employee_id',
            'holiday_type',
            'number_of_days',
            'mode_company_id'
        ],
        'new_model_name': 'hr.leave.allocation'
    },
    'hr.leave.type': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'hr.leave.type'
    },
    'mail.message': {
        'create': True,
        'extra_args': {},
        'include_archived': False,
        'key_fields': [
            'subject',
            'date',
            'model',
            'res_id',
            'body',
            'message_type'
        ],
        'new_model_name': 'mail.message'
    },
    'res.company': {
        'create': False,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['id'],
        'new_model_name': 'res.company'
    },
    'res.country': {
        'create': False,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['code'],
        'new_model_name': 'res.country'
    },
    'res.country.state': {
        'create': False,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['code', 'name'],
        'new_model_name': 'res.country.state'
    },
    'res.currency': {
        'create': False,
        'extra_args': {},
        'include_archived': True,
        'key_fields': ['name'],
        'new_model_name': 'res.currency'
    },
    'res.partner': {
        'create': True,
        'extra_args': {},
        'include_archived': True,
        'key_fields': ['name', 'type'],
        'new_model_name': 'res.partner'
    },
    'res.partner.title': {
        'create': False,
        'extra_args': {},
        'include_archived': False,
        'key_fields': ['name'],
        'new_model_name': 'res.partner.title'
    },
    'res.users': {
        'create': True,
        'domain': [('login', '!=', ''), ('id', 'not in', [1, 2])],
        'include_archived': True,
        'key_fields': ['login', 'name'],
        'new_model_name': 'res.users'}
}
