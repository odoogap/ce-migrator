import os
import ast
import inspect


DISABLED_MAIL_CONTEXT = {
    'tracking_disable': True,
    'mail_create_nolog': True,
    'mail_create_nosubscribe': True,
    'mail_notrack': True,
    'no_reset_password': True,
    'leave_skip_date_check': True,
}


class MigrationError(Exception):
    pass


def rename_id(record):
    record['x_old_id'] = record['id']
    del record['id']
    return record


def get_first_from_id(record):
    for k, v in record.items():
        if type(v) in (list, tuple) and k.endswith('_id'):
            record[k] = v[0]
    return record


def rec_to_str(rec):
    return "%s" % rec.get('name', rec.get('id'))


class MigrateToolBase(object):

    def __init__(self, env, connection, verbose=False):
        self.env = env
        self.connection = connection
        self.model_name = 'res.partner'
        self.verbose = verbose
        model_methods = dir(self)
        self.post_methods = {key.replace('post_', '').replace('_', '.'): key for key in
                             filter(lambda m: m.startswith('post_'), model_methods)}
        self.transform_methods = {key.replace('transform_', '').replace('_', '.'): key for key in filter(
            lambda m: m.startswith('transform_'), model_methods)}
        self._recalc_model()

    def ensure_old_id(self, model_name):
        model = self.env['ir.model'].search([('model', '=', model_name)])
        has_old_id = self.env['ir.model.fields'].search([
            ('name', '=', 'x_old_id'),
            ('model_id', '=', model.id)
        ])
        if not has_old_id:
            data = {
                'name': 'x_old_id',
                'field_description': 'Old ID',
                'ttype': 'integer',
                'help': 'Technical field used for migration',
                'required': False,
                'index': True,
                'copied': False,
                'related': False,
                'depends': False,
            }
            model.write({'field_id': [(0, 0, data),]})
            self.env.cr.commit()

    def _recalc_model(self):
        # from remote server
        self.origin_fields = self._get_origin_model_fields(self.model_name)
        # from this server >= v16
        self.new_model_name = self._get_field_info_dict(self.model_name)['new_model_name']
        self.target_fields = self._get_local_model_fields(self.new_model_name)
        self.ensure_old_id(self.new_model_name)
        # calculate diff
        self.diff = self._compare_lists(self.origin_fields, self.target_fields, verbose=False)
        self.matching_fields = filter(lambda x: self.diff[x]['origin'] and self.diff[x]['target'],
                                      self.origin_fields.keys())
        self.iprint("................. model_name / new_model_name: ", self.model_name, self.new_model_name, verbose=True)
        self.matching_char_fields = [
            field_name for field_name in filter(
                lambda x: self.diff[x]['origin'] == 'char' and self.diff[x]['target'] in (
                    'char', 'text', 'boolean', 'selection'),
                self.origin_fields.keys())
        ]
        self.iprint("................. matching_char_fields : ", self.matching_char_fields, verbose=True)
        self.matching_many2one_fields = [
            (field_name, self.target_fields[field_name]['relation']) for field_name in filter(
                lambda x: self.diff[x]['origin'] == 'many2one' and
                          self.diff[x]['target'] == 'many2one' and
                          'relation' in self.target_fields[x],
                self.target_fields.keys())
        ]

    def set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(key, value)

    def iprint(self, *args, verbose=False):
        cur_frame = inspect.currentframe()
        cal_frame = inspect.getouterframes(cur_frame, 2)
        caller_name = cal_frame[1][3]
        if verbose or self.verbose:
            print("\x1b[1m[%s]:\x1b(B\x1b[m " % caller_name, *args)

    def _compare_lists(self, origin, target, verbose=False):
        cp = {}
        for item in origin.keys():
            cp[item] = {'origin': origin[item]['type'], 'target': ''}
        for item in target.keys():
            if item in cp:
                cp[item].update({'target': target[item]['type']})
            else:
                cp[item] = {'origin': '', 'target': target[item]['type']}

        for i in cp:
            self.iprint("%-50s" % i, "%(origin)-10s %(target)-10s " % cp[i], verbose=verbose)
        return cp

    def ensure_model(self, model_name):
        if self.model_name != model_name:
            self.model_name = model_name
            self._recalc_model()

    def _get_field_info_dict(self, model_name):
        config_path = os.environ.get('CEMIG_CONFIG', False)
        try:
            config_path = os.path.expanduser(config_path)
            with open(config_path, 'rb') as cfg:
                res = ast.literal_eval(cfg.read().decode('latin1'))
            for key in res:
                extra_args = res[key].get('extra_args')
                if not extra_args:
                    res[key]['extra_args'] = {}
                if key in self.post_methods:
                    res[key]['extra_args']['post_run'] = self.post_methods[key]
                if key in self.transform_methods:
                    res[key]['extra_args']['transform'] = self.transform_methods[key]
            return res[model_name]
        except Exception:
            raise MigrationError('You need to define CEMIG_CONFIG environment variable')

    def _get_local_model_fields(self, model_name):
        return self.env[model_name].fields_get()

    def _get_origin_model_fields(self, model_name):
        return self.connection.get_model(model_name).fields_view_get()['fields']

    def copy_chatter(self, model_name):
        self.ensure_model(model_name)
        info = self._get_field_info_dict(model_name)
        key_fields, include_archived, new_model_name, create_record, extra_args = \
            info['key_fields'], info['include_archived'], info['new_model_name'], info['create'], info['extra_args']
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        rs_partner = self.env['res.partner'].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        domain = []
        for rec in remote_rs.search_read(domain, ['message_ids'], order="create_date DESC"):
            local_rec = rs.search([('x_old_id', '=', rec['id'])], limit=1)
            if len(local_rec.message_ids) == len(rec['message_ids']):
                self.iprint("Nothing to import for x_old_id=%s" % rec['id'], verbose=True)
                continue
            if local_rec and len(local_rec.message_ids) != len(rec['message_ids']):
                for msg in self.connection.get_model('mail.message').search_read([
                    ('id', 'in', rec['message_ids'])],
                        [
                            'author_id',
                            'subject',
                            'body',
                            'email_from',
                            'reply_to',
                            'message_type',
                            'message_id',
                            'description',
                            'date'
                        ]):
                    author_rec = rs_partner.search([('x_old_id', '=', msg['author_id'][0])], limit=1)
                    local_rec.message_post(
                        email_from=msg['email_from'],
                        reply_to=msg['reply_to'],
                        date=msg['date'],
                        message_type=msg['message_type'],
                        message_id=msg['message_id'],
                        subject=msg['subject'],
                        description=msg['description'],
                        body=msg['body'],
                        author_id=author_rec.id
                    )
            else:
                self.iprint("ERROR: No lead found for x_old_id=%s" % rec['id'], verbose=True)
        self.env.cr.commit()

    def import_basic_types(self, model_name, force_fields=None):
        """It will import all : 'char', 'text', 'boolean', 'selection' type fields that have the same name.
        Use force fields to force them.

        :param model_name:
        :param force_fields:
        :return:
        """
        if force_fields is None:
            force_fields = []
        self.ensure_model(model_name)

        self.iprint("\n import chars: %s \n" % (self.model_name), verbose=True)
        def different_items(y, x): return {k: x[k] for k in x if k in y and x[k] != y[k]}
        info = self._get_field_info_dict(model_name)
        key_fields, include_archived, new_model_name, create_record, extra_args = \
            info['key_fields'], info['include_archived'], info['new_model_name'], info['create'], info['extra_args']
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        transform_name = extra_args.get('transform', False)
        field_list = self.matching_char_fields
        if force_fields:
            field_list.extend(force_fields)

        for rec in remote_rs.search_read([], field_list):
            local_rec = rs.search([('x_old_id', '=', rec['id'])])
            if transform_name:
                transform = getattr(self, transform_name)
                rec, key_fields = transform(rec, key_fields)
            if not local_rec:
                rec = rename_id(rec)
                local_rec = rs.create(rec)
            else:
                existing_rec_vals = local_rec.read([])[0]
                existing_rec_vals.pop('id', None)
                diff_dict = different_items(existing_rec_vals, rec)

                if diff_dict:
                    local_rec.write(diff_dict)
        self.env.cr.commit()

    def update_many2one_fields(self, model_name, fields, verbose=False):
        """Run after you are happy with the result of check_fixed_models"""
        self.ensure_model(model_name)
        new_model_name = self._get_field_info_dict(model_name)['new_model_name']
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        for rec in remote_rs.search_read([], fields):
            match = rs.search([('x_old_id', '=', rec['id'])])
            if match:
                vals = {}
                for fld in fields:
                    match_model = self.target_fields[fld]['relation']
                    if rec[fld]:
                        vals[fld] = self.env[match_model].search([('x_old_id', '=', rec[fld][0])]).id
                if vals:
                    match.write(vals)
        self.env.cr.commit()

    def update_many2many_fields(self, model_name, fields, verbose=False):
        """Run after you are happy with the result of check_fixed_models"""
        self.ensure_model(model_name)
        new_model_name = self._get_field_info_dict(model_name)['new_model_name']
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        for rec in remote_rs.search_read([], fields):
            match = rs.search([('x_old_id', '=', rec['id'])])
            if match:
                vals = {}
                for fld in fields:
                    match_model = self.target_fields[fld]['relation']
                    if rec[fld]:
                        vals[fld] = self.env[match_model].search([('x_old_id', 'in', rec[fld])]).ids
                if vals:
                    vals_conv = {k: [(6, 0, v)] for k, v in vals.items()}
                    match.write(vals_conv)
                    self.env.cr.commit()

    def update_one2many_fields(self, model_name, field, extra_domain=[], create=True, verbose=False):
        """Update existing record with one2many. Doesn't create new records on model_name"""
        self.ensure_model(model_name)
        new_model_name = self._get_field_info_dict(model_name)['new_model_name']
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        for rec in remote_rs.search_read([], [field], limit=100):
            target_record = rs.search([('x_old_id', '=', rec['id'])])

            if target_record:
                # get relation model
                relation_model = self.target_fields[field]['relation']
                relation_field = self.target_fields[field]['relation_field']
                relation_domain_filter = self.target_fields[field]['domain']
                # get mapping for the relation model

                new_model_name = self._get_field_info_dict(relation_model)['new_model_name']
                related_rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
                related_key_fields = self._get_field_info_dict(relation_model)['key_fields']
                extra_args = self._get_field_info_dict(relation_model)['extra_args']
                transform_name = extra_args.get('transform', False)
                related_domain = relation_domain_filter + [(relation_field, '=', rec['id'])] + extra_domain

                for ro_id in self.connection.get_model(relation_model).search(related_domain):
                    rel_match = related_rs.search([('x_old_id', '=', ro_id)])

                    if rel_match:
                        self.iprint("|---> updating ", new_model_name)
                    else:
                        self.iprint("|---> creating ", new_model_name, related_key_fields)
                        [vals] = self.connection.get_model(relation_model).search_read([('id', '=', ro_id)], related_key_fields)

                        if vals and transform_name:
                            transform = getattr(self, transform_name)
                            vals = transform(vals)
                        vals = rename_id(vals)
                        vals = get_first_from_id(vals)

                        self.iprint("::::--- vals: ", vals, verbose=True)
                        if vals:
                            self.iprint("|---> vals: ", vals)
                            related_rs.create(vals)
            else:
                self.iprint("-- no target record to update, you need to create them first")

        self.env.cr.commit()

    def _convert_id_records(self, model_name, rec):
        for k, v in rec.items():
            if k.endswith('_id') and v:
                rel_model = self._get_origin_model_fields(model_name)[k]['relation']
                rel_model = self._get_field_info_dict(rel_model)['new_model_name']
                domain_m21 = ['|', ('active', '=', False), ('active', '=', True), ('x_old_id', '=', rec[k][0])]
                new_id = self.env[rel_model].with_context(**DISABLED_MAIL_CONTEXT).search(domain_m21)
                if len(new_id) == 0:
                    rec[k] = False
                elif len(new_id) == 1:
                    rec[k] = new_id.id
                elif len(new_id) == 2:
                    rec[k] = new_id.filtered(lambda x: x.active is True)[0].id
                else:
                    raise Exception('More/less than one match for the same x_old_id %s - x_old_id=%s' % (new_id, rec[k][0]))
        return rec

    def _handle_record(self, rs_model, key_fields, archived, create, record):
        domain = archived and ['|', ('active', '=', False), ('active', '=', True)] or []
        # if key field is a "*_id" will return a <list>
        domain.extend([(f, '=', record[f][0]) if type(record[f]) is list else (f, '=', record[f]) for f in key_fields])
        match = rs_model.search(domain)
        if len(match) > 1:
            raise Exception('More than one match for the same x_old_id')
        if match:
            if match.x_old_id < 0 or not match.x_old_id:
                match.x_old_id = record['id']
            return match
        else:
            self.iprint("no match: ", record, match)
            if create:
                record['x_old_id'] = record['id']
                record.pop('id', None)
                res = rs_model.create(record)
                return res
            else:
                return False

    def init_import_models(self, model_name):
        """First check that things match and add the id of the origin to the new db
        This will also print records that don't match but sometimes doesn't matter

        :return:
        """
        info = self._get_field_info_dict(model_name)
        self.ensure_model(model_name)
        key_fields, include_archived, new_model_name, create_record, extra_args = \
            info['key_fields'], info['include_archived'], info['new_model_name'], info['create'], info['extra_args']
        domain_extra = extra_args.get('domain', [])
        post_run_name = extra_args.get('post_run', False)
        transform_name = extra_args.get('transform', False)
        self.iprint("\n Initiate import ------ model name: ", model_name)
        rs = self.env[new_model_name].with_context(**DISABLED_MAIL_CONTEXT)
        remote_rs = self.connection.get_model(model_name)
        domain = include_archived and ['|', ('active', '=', False), ('active', '=', True)] or []
        domain.extend(domain_extra)

        for rec in remote_rs.search_read(domain, key_fields + ['active'], order="id"):
            match = rs.search([('x_old_id', '=', rec['id'])])
            if match:
                self.iprint("    Already exists record model %s: %s" % (new_model_name or model_name, rec_to_str(rec)))
            else:
                self.iprint("    Importing record model %s: %s" % (new_model_name or model_name, rec_to_str(rec)))
                if transform_name:
                    transform = getattr(self, transform_name)
                    rec, key_fields_target = transform(rec, key_fields)
                else:
                    key_fields_target = key_fields

                if rec.get('parent_id', False):
                    parent_id = rec.get('parent_id', False)[0]
                    # first create the parent
                    [parent_rec] = remote_rs.search_read([('id', '=', parent_id)], key_fields)
                    parent_rec.pop('parent_id', None)
                    local_parent_id = self._handle_record(
                        rs, key_fields_target, include_archived, create_record, parent_rec)
                    # then create the child
                    rec['parent_id'] = local_parent_id.id
                    local_id = self._handle_record(rs, key_fields_target, include_archived, create_record, rec)
                    records = [local_parent_id, local_id]
                else:
                    rec = self._convert_id_records(model_name, rec)
                    res = self._handle_record(rs, key_fields_target, include_archived, create_record, rec)
                    records = [res]

                if post_run_name:
                    post_run = getattr(self, post_run_name)
                    post_run(records)
        self.env.cr.commit()

    def print_diff(self, model_name):
        self.ensure_model(model_name)
        self.iprint("\n\tComparing origin model: %s with targe model: %s\n" % (model_name, self.new_model_name), verbose=True)
        self._compare_lists(self.origin_fields, self.target_fields, verbose=True)
