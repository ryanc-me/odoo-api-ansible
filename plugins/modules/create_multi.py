#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: create_multi
short_description: Create multiple new records
description:
  - Create multiple new records
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
            - A list of dictionaries, each containing values for one new record
        type: list
        required: true
"""
EXAMPLES = r"""
- name: Create multiple new partners
  odoo.api.create_multi:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    values:
      - name: "Test 1"
        email: "hello@example.com"
      - name: "Test 2"
        email: "goodbye@example.com"
  register: result

- name: Display the result
  debug:
    msg: "ids: {{ result.ids }}"
"""
RETURN = r"""
ids:
    description: A list of ids for the new records
    type: list
    returned: success
    sample: [1, 2]
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
        values=dict(type="list", required=False),
    )

    result = dict(changed=False, ids=False)

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
            record_ids = client.create(
                module.params["model"],
                module.params["values"],
            )
            result.update({
                "changed": True,
                "ids": record_ids
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
