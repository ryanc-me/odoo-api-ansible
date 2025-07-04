#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: read
short_description: Read data from record(s)
description:
  - Read data from record(s)
author:
  - Ryan Cole (@ryanc-me)
options:
    url:
        description:
            - The URL of the Odoo instance.
        type: str
        required: true
    database:
        description:
            - The name of the Odoo database.
        type: str
        required: true
    username:
        description:
            - The username to login with.
        type: str
        required: true
    password:
        description:
            - The password to login with.
        type: str
        required: true
    model:
        description:
            - The Odoo model to execute on
        type: str
        required: true
    ids:
        description:
            - A list of ids to read from
        type: list
        required: true
    fields:
        description:
            - A list of fields to read
        type: list
        required: false
"""
EXAMPLES = r"""
- name: Fetch the name/email for the first 2 users (ids = 1, 2)
  odoo.api.read:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    ids: [1, 2]
    fields: ["name", "email"]
  register: result

- name: Display the result
  debug:
    msg: "data: {{ result.data }}"
"""
RETURN = r"""
data:
    description: Data that was read from the records, as a list of dictionaries
    type: list
    returned: success
    sample: [{"id": 1, "name": "hello"}, ...]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import urlparse
from ansible_collections.odoo.api.plugins.module_utils import odoo_api, utils


def run_module():
    module_args = dict(
        url=dict(type="str", required=True),
        database=dict(type="str", required=True),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
        model=dict(type="str", required=True),
        ids=dict(type="list", required=True),
        fields=dict(type="list", required=False),
    )

    result = dict(changed=False, data=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        client = odoo_api.OdooClient(
            url=module.params["url"],
            database=module.params["database"],
            username=module.params["username"],
            password=module.params["password"],
        )
        try:
            data = client.read(
                module.params["model"],
                utils.check_ids(module.params["ids"]),
                fields=module.params["fields"],
            )
            result.update({
                "data": data
            })
        except odoo_api.OdooConnectionError as e:
            raise Exception("Could not connect") from e
        except odoo_api.OdooJsonRpcError as e:
            raise Exception("Malformed response") from e
    except Exception as e:
        module.fail_json(msg=str(e))
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
