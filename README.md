# odoo-api-ansible

Odoo JSON-RPC API bindings for Ansible

### Goals

 * Implement all of the core JSON-RPC APIs (common, db, object), and offer all args/kwargs, where reasonably possible.
 * No dependencies on Odoo API libraries (this module crafts its own JSON-RPC requests)
 * Be a relatively thin wrapper over the API - not too much fluff.

### Install

See [Installing a collection from a Git repository](https://docs.ansible.com/ansible/latest/collections_guide/collections_installing.html#installing-a-collection-from-a-git-repository)

```bash
ansible-galaxy collection install git@github.com:ansible-collections/collection_template.git
```

### Examples

`search_read`
```yaml
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
```

`create`
```yaml
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
```

`execute_kw`
```yaml
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
```