#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: execute_kw
short_description: Execute a method on an Odoo mode with positional and keyword args
description:
  - Execute a method on an Odoo model, optionally passing some positional or keyword args, and return the result
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
    method:
        description:
            - The method to execute
        type: str
        required: true
    args:
        description:
            - The arguments to pass
        type: list
        required: false
    kwargs:
        description:
            - The keyword arguments to pass 
        type: dict
        required: false
"""
EXAMPLES = r"""
- name: Fetch the email address for the first partner called "Test"
  odoo.api.execute_kw:
    url: "{{ odoo_url }}"
    database: "{{ odoo_database }}"
    username: "{{ odoo_username }}"
    password: "{{ odoo_password }}"
    model: "res.partner"
    method: "search_read"
    kwargs:
      domain: [["name", "=", "Administrator"]]
      fields: ["email"]
  register: result

- name: Display the result
  debug:
    msg: "result: {{ result.res }}"
"""
RETURN = r"""
res:
    description: The result passed back from Odoo
    type: complex
    returned: success
    sample: true
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
        method=dict(type="str", required=True),
        args=dict(type="list", required=False),
        kwargs=dict(type="dict", required=False),
    )

    result = dict(changed=False, res=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # could technically be a non-updating query, but to be safe, we will exit
    # early regardless
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
            res = client.model_execute_kw(
                module.params["model"],
                module.params["method"],
                module.params["args"],
                module.params["kwargs"],
            )
            result["res"] = res
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
