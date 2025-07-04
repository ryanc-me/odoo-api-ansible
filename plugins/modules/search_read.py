#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: search_read
short_description: Perform a search, then a read, in one operation
description:
  - Perform a search, then a read, in one operation
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
    domain:
        description:
            - A search domain. Use an empty list to match all records
        type: list
        required: false
    fields:
        description:
            - A list of fields to read
        type: list
        required: false
    offset:
        description:
            - Number of records to ignore
        type: int
        required: false
    limit:
        description:
            - Maximum number of records to return
        type: int
        required: false
    order:
        description:
            - A sort string
        type: str
        required: false
    load: 
        description:
            - Loading mode, pass `False` to avoid computing display_name
        type: bool
        required: false
"""
EXAMPLES = r"""
- name: Read name/email from the newest partner whose email ends with @example.com,
  odoo.api.search_read:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    domain: [["email", "=ilike", "%@example.com"]]
    limit: 1
    order: create_date desc
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
from ansible_collections.odoo.api.plugins.module_utils import odoo_api


def run_module():
    module_args = dict(
        url=dict(type="str", required=True),
        database=dict(type="str", required=True),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
        model=dict(type="str", required=True),
        domain=dict(type="list", required=False),
        fields=dict(type="list", required=False),
        offset=dict(type="int", required=False),
        limit=dict(type="int", required=False),
        order=dict(type="str", required=False),
        load=dict(type="bool", required=False),
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
            data = client.search_read(
                module.params["model"],
                domain=module.params["domain"],
                fields=module.params["fields"],
                offset=module.params["offset"],
                limit=module.params["limit"],
                order=module.params["order"],
                load=module.params["load"],
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
