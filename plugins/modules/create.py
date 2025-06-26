#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: create
short_description: Create a new record
description:
  - Create a new record
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
    values:
        description:
            - Values for the new record
        type: dict
        required: true
"""
EXAMPLES = r"""
- name: Create a new partner
  odoo.api.create:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    values:
      name: Test Partner
      email: "hello@example.com"
  register: result

- name: Display the result
  debug:
    msg: "id: {{ result.id }}"
"""
RETURN = r"""
id:
    description: The id of the new record
    type: int
    returned: success
    sample: 1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import urlparse
from ansible_collections.odoo.api.plugins.module_utils import odoo_api


def run_module():
    module_args = dict(
        url=dict(type="str", required=True),
        database=dict(type="str", required=True),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
        model=dict(type="str", required=True),
        values=dict(type="dict", required=False),
    )

    result = dict(changed=False, id=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    try:
        client = odoo_api.OdooClient(
            url=module.params["url"],
            database=module.params["database"],
            username=module.params["username"],
            password=module.params["password"],
        )
        try:
            record_id = client.create(
                module.params["model"],
                module.params["values"],
            )
            result["id"] = record_id
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
