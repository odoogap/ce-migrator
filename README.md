# Odoo CE Migrator

## Introduction

This module imports Odoo models in a simple way. It's a shell script that connects through JSONRPC to the old version and
creates the records in the new version server.

It will create an x_old_id integer field on all imported models. This x_old_id is used by the script to get the link info
on each record.

## Creating the shell script

Create a new script, anywhere you like. It doesn't need to be inside any module.

`migrate.py`

```python
import os
import odoolib
from cemigrate import MigrateToolBase, DISABLED_MAIL_CONTEXT


class MigrateTool(MigrateToolBase):

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
            [user_dict] = remote_rs.search_read([('id', '=', user.x_old_id)], ['partner_id'])
            user.partner_id.x_old_id = user_dict['partner_id'][0]

            
connection = odoolib.get_connection(
        hostname=os.environ.get('OLD_HOSTNAME', "localhost"),
        database=os.environ.get('OLD_DATABASE', "v12_odoo"),
        login=os.environ.get('OLD_LOGIN', "admin"),
        password=os.environ.get('OLD_PASSWORD', "admin"),
        port=int(os.environ.get('OLD_PORT', 443)),
        protocol=os.environ.get('OLD_PROTOCOL', "jsonrpcs")
)

mt = MigrateTool(env, connection, False)

# base objects
mt.init_import_models('res.country')
mt.init_import_models('res.country.state')
mt.init_import_models('res.currency')
# users partners
mt.init_import_models('res.partner')
mt.init_import_models('res.users')
mt.import_basic_types('res.partner')
mt.update_many2one_fields('res.partner', ['country_id', 'state_id', 'parent_id'])
# leads
mt.init_import_models('crm.lead.tag')
mt.init_import_models('crm.stage')
mt.import_basic_types('crm.lead')
mt.init_import_models('crm.team')
mt.update_many2one_fields('crm.lead', ['user_id', 'country_id', 'stage_id', 'team_id', 'company_currency'])
mt.update_many2many_fields('crm.lead', ['tag_ids'])

```

Check for a more complete example at: `samples/migrate12-16.py`


## Running the shell script

Create a new database with your custom modules installed, without any data.
First load you .env file (check the env.sample with the environment variables)

```bash
# Load the variables in the envionment
source .env

# Run the script making sure you have the complete path to odoo-bin
odoo-bin shell \
    --addons-path ~/git/odoo/16.0/addons,~/git/odoo-themes/16.0,~/dev/custom \
    -d v16_newdb --no-http --max-cron-threads=0 < migrate.py
```

## How does it work?

First we initialize the model with key fields

```python
mt.init_import_models('res.partner')
```

Now that we have the new record with new (id) and (x_old_id) reference we can import other fields.
The config file uses key_fields concept, meaning that your match e.g name=old.name and city=old.city to initialize.
Doing this, will import all 'char', 'text', 'boolean', 'selection' fields that have the same name and type. 

```python
mt.import_basic_types('res.partner', [])
```

Since the fields 'customer' and 'supplier' have been changed to 'customer_rank' and 'supplier_rank'.
Because they don't exist, we need to force them and use (def transform_res_partner) for conversion.

```python
mt.import_basic_types('res.partner',  ['customer', 'supplier'])
```

and we also need to add the method: *transform_res_partner*

```python
class MigrateTool(MigrateToolBase):

    def transform_res_partner(self, vals, key_fields):
        vals['customer_rank'] = vals.get('customer', False) and 1 or 0
        vals['supplier_rank'] = vals.get('supplier', False) and 1 or 0
        vals.pop('customer', None)
        vals.pop('supplier', None)
        return vals, key_fields
```

Now we can focus on Many2one fields:

```python
mt.update_many2one_fields('res.partner', ['country_id', 'state_id', 'parent_id'])
```

Just be sure to initialize the related models first. In this case 'res.country' and 'res.country.state'.
