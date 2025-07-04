#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: db_list_countries
short_description: Get a list of valid country codes
description:
  - Get a list of valid country codes
author:
  - Ryan Cole (@ryanc-me)
options:
    url:
        description:
            - The URL of the Odoo instance.
        type: str
        required: true
    master_passwd:
        description:
            - The master password
        type: str
        required: true
"""
EXAMPLES = r"""
- name: Get a list of valid country codes
  odoo.api.db_list_countries:
    url: "{{ odoo_url }}"
    master_passwd: "{{ master_password }}"
  register: result

- name: Display the result
  debug:
    msg: "id: {{ result.id }}"
"""
RETURN = r"""
countries:
    description: A list of (code, name) pairs
    type: list
    returned: success
    sample: [("NZ", "New Zealand"), ("AU", "Australia")]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import urlparse
from ansible_collections.odoo.api.plugins.module_utils import odoo_api


def run_module():
    module_args = dict(
        url=dict(type="str", required=True),
        master_passwd=dict(type="str", required=True, no_log=True),
    )

    result = dict(changed=False, countries=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        client = odoo_api.OdooClient(
            url=module.params["url"],
        )
        try:
            countries = client.db_list_countries(
                module.params["master_passwd"],
            )
            result.update({
                "countries": countries
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
