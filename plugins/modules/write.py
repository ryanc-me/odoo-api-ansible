#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: write
short_description: Write data to some record(s)
description:
  - Write data to some record(s)
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
            - A list of ids to write to
        type: list
        required: true
    values:
        description:
            - The data to write
        type: dict
        required: true
"""
EXAMPLES = r"""
- name: Update the email address for partner ids 1, 2
  odoo.api.write:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    ids: [1, 2]
    values:
      email: hello@example.com
  register: result

- name: Display the result
  debug:
    msg: "okay: {{ result.okay }}"
"""
RETURN = r"""
okay:
    description: True if the request succeeded
    type: bool
    returned: success
    sample: True
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
        values=dict(type="dict", required=True),
    )

    result = dict(changed=False, okay=False)

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
            okay = client.write(
                module.params["model"],
                utils.check_ids(module.params["ids"]),
                module.params["values"],
            )
            result["okay"] = okay
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
