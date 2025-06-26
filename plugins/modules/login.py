#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: login
short_description: Login to Odoo, returning the ID of the user
description:
  - Login to Odoo, returning the ID of the user.
  - Note: This does not need to be run before other Odoo modules, as they will handle authentication automatically.
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
"""
EXAMPLES = r"""
- name: Login to Odoo
  odoo.api.login:
    url: "https://odoo.example.com"
    database: "my_database"
    username: "my_username"
    password: "my_password"
  register: odoo_user_id

- name: Print Odoo user ID
  debug:
    msg: "Logged in user ID is {{ odoo_user_id.id }}"
"""
RETURN = r"""
uid:
    description: The ID of the logged-in user.
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
    )

    result = dict(changed=False, uid=None)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        client = odoo_api.OdooClient(
            url=module.params["url"],
            database=module.params["database"],
            username=module.params["username"],
            password=module.params["password"],
        )
        try:
            uid = client.authenticate()
        except odoo_api.OdooConnectionError as e:
            raise Exception("Could not connect") from e
        except odoo_api.OdooJsonRpcError as e:
            raise Exception("Malformed response") from e
        if not uid:
            raise Exception("Authentication failed")
        result["uid"] = uid
    except Exception as e:
        module.fail_json(msg=str(e))
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
