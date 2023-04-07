# Odoo CE Migrator

## Introduction

This module imports Odoo models in a simple way. It's a shell script that connects through JSONRPC to the old version and
creates the records in the new version server.

It will require you to create a new field in all models using the following code:

`models/base.py`
```python
from odoo import models, fields


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    old_id = fields.Integer(help='Used to save the old ID for import', default=-1)

```

Add this to your new version custom models
This old_id is used by the script to get the link info on each record.

## Creating the shell script

Create a new script, anywhere you like. It doesn't need to be inside any module.

`migrate.py`
```python
import os
import odoolib
from cemigrate import MigrateTool
print("""
---------------------------------------------------------------------
""")

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
mt.import_chars('res.partner')
mt.update_many2one_fields('res.partner', ['country_id', 'state_id', 'parent_id'])
# leads
mt.init_import_models('crm.lead.tag')
mt.init_import_models('crm.stage')
mt.import_chars('crm.lead')
mt.init_import_models('crm.team')
mt.update_many2one_fields('crm.lead', ['user_id', 'country_id', 'stage_id', 'team_id', 'company_currency'])
mt.update_many2many_fields('crm.lead', ['tag_ids'])

```


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
