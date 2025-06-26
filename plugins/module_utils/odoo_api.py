from ansible.module_utils.urls import open_url
from urllib.parse import urljoin
import json


class OdooError(Exception):
    """Base class for Odoo-related errors"""

    pass


class OdooAuthenticationError(OdooError):
    """Raised when authentication fails"""

    def __init__(self, message="Authentication failed, please check your credentials."):
        super().__init__(message)


class OdooConnectionError(OdooError):
    """Raised when there's some HTTP-related error, such as a connection failure"""

    def __init__(self, url, message="Could not connect to the Odoo server."):
        super().__init__(message + f"\n\nURL: {url}")


class OdooJsonRpcError(OdooError):
    """Raised when the JSON-RPC response is invalid or contains an error"""

    def __init__(self, message, code, data):
        message = f"JSON-RPC Error (code: {code}): {message}"
        if data and isinstance(data, dict):
            if "message" in data:
                message += f"\n\nMessage: {data['message']}"
            if "debug" in data:
                message += f"\n\nData: {data['debug']}"
        super().__init__(message)
        self.code = code
        self.data = data


class OdooClient:
    """Minimal Odoo JSON-RPC client

    This class aims to provide sugar around the raw JSON-RPC API, and to
    implement all of Odoo's core "service" methods (e.g., authenticate, execute,
    execute_kw, etc).

    Goals:
     1) Provide an easy-to-user interface (i.e., no manual de/serialisation)
     2) Implement all of the core Odoo service methods (incl. db and common)
     3) Use Ansible's `module_utils.urls` wherever possible
     4) Avoid reliance on other Python libraries, so that it remains portable

    References (Odoo 18.0 as of 2025-06-25):
     - https://github.com/odoo/odoo/blob/a87602a2/odoo/addons/base/controllers/rpc.py#L178
     - https://github.com/odoo/odoo/blob/a87602a2/odoo/http.py#L379
     - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L56
     - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L22-L29
    """

    RPC_ENDPOINT = "/jsonrpc"
    RPC_VERSION = "2.0"
    RPC_ID = 1

    def __init__(
        self, url, database, password=False, username=False, uid=False, debug=False
    ):
        if not uid and not username:
            raise ValueError("Either uid or username must be provided")

        self.url = url
        self.database = database
        self.password = password
        self.username = username
        self.uid = uid

    def _jsonrpc(
        self, service, method, arguments, http_method="post", check_status=True
    ):
        """Base JSON-RPC method

        :param params: Parameters to send in the request body
        :param method: HTTP method to use (default: 'post')
        :return: The `result` field from the JSON-RPC response
        """
        # bundle the request body
        endpoint = urljoin(self.url, self.RPC_ENDPOINT)
        body = {
            "jsonrpc": self.RPC_VERSION,
            "method": "call",
            "id": self.RPC_ID,
            "params": {
                "service": service,
                "method": method,
                "args": arguments,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = open_url(
                endpoint,
                method=method,
                data=json.dumps(body, default=str),
                headers=headers,
            )

            if check_status and resp.status != 200:
                raise Exception(f"HTTP Error {resp.status}: {resp.reason}")
        except Exception as e:
            raise OdooConnectionError(endpoint) from e

        # unbundle
        data = "Unable to Parse"
        try:
            data = resp.read()
            data = json.loads(data)
            if "error" in data:
                error = data["error"]
                raise OdooJsonRpcError(
                    message=error.get("message", "Unknown error"),
                    code=error.get("code", -1),
                    data=error.get("data", {}),
                )
            if "result" not in data:
                raise Exception("Response does not contain 'result' field")
            return data["result"]
        except Exception as e:
            raise OdooConnectionError(endpoint) from e

    def _check_login(self):
        """Check that the user is logged in, or authenticate if not

        Note that "authenticating" is really just getting the users' ID, via
        the `authenticate` method. Other Odoo methods (like execute, execute_kw)
        expect the `uid` param. We allow the library user to pass either the
        uid, or a username. In the latter case, we'll fetch the uid here (at the
        cost of 1 extra request).

        Call this method at the start of any method that requires authentication.

        :return: None
        :raises OdooAuthenticationError: If authentication fails
        """
        if not self.uid:
            try:
                self.uid = self.authenticate()
            except OdooConnectionError as e:
                raise OdooAuthenticationError(
                    "Odoo connection failed during authentication"
                ) from e
            except OdooJsonRpcError as e:
                raise OdooAuthenticationError(
                    "Invalid JSON-RPC response during authentication"
                ) from e

    def login(self):
        return self.authenticate()

    def authenticate(self):
        self.uid = self.common_authenticate(self.database, self.username, self.password)
        return self.uid

    ### services/common

    def common_login(self, db, login, password):
        """Authenticate with Odoo using the provided credentials

        Note: this is just a wrapper around the `authenticate` method.

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L19-L20

        :param db: Database to authenticate against
        :param login: Username or email to authenticate
        :param password: Password for the user
        :return: The user ID if authentication is successful
        :raises OdooAuthenticationError: If authentication fails
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [db, login, password]
        return self._jsonrpc("common", "login", arguments, http_method="get")

    def common_authenticate(self, db, login, password, user_agent_env=None):
        """Authenticate a user against the Odoo server

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L22-L29

        :param db: Database to authenticate against
        :param login: Username or email to authenticate
        :param password: Password for the user
        :param user_agent_env: Optional user agent environment string
        :return: The user ID if authentication is successful
        :raises OdooAuthenticationError: If authentication fails
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [db, login, password, user_agent_env]
        return self._jsonrpc("common", "authenticate", arguments, http_method="get")

    def common_version(self):
        """Fetch some version info about Odoo

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L31-L32
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L12-L17

        :return: A dictionary containing the Odoo version information (see reference #2)
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        return self._jsonrpc("common", "version", False, http_method="get")

    def common_about(self, extended=False):
        """Fetch the Odoo version number and other details

        This is a strange method - by default (extended=False), it simply
        returns "See https://openerp.com". With extended=True, it returns
        the previous string, along with the Odoo version number.

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/common.py#L34-L45

        :param extended: Whether to return extended version information
        :return: The Odoo URL (default) or a tuple of (url, version) if extended=True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [extended]
        return self._jsonrpc("common", "about", arguments, http_method="get")

    ### services/db

    def database_create(
        self,
        master_password,
        db_name,
        demo,
        lang,
        user_password="admin",
        login="admin",
        country_code=None,
        phone=None,
    ):
        """Create a new Odoo database

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L145-L150

        :param master_password: Master password for the Odoo server
        :param db_name: Name of the new database
        :param demo: Whether to load demo data (True/False)
        :param lang: Language code for the new database (e.g., 'en_US')
        :param user_password: Password for the admin user (default: 'admin')
        :param login: Username for the admin user (default: 'admin')
        :param country_code: Country code for localizations (optional, impl. default is US)
        :param phone: Phone number for the admin user (optional)
        :return: True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [
            master_password,
            db_name,
            demo,
            lang,
            user_password,
            login,
            country_code,
            phone,
        ]
        return self._jsonrpc("db", "create_database", arguments)

    def database_duplicate(
        self, master_password, db_original_name, db_name, neutralize=False
    ):
        """Duplicate an existing Odoo database

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L153-L178

        :param master_password: Master password for the Odoo server
        :param db_original_name: Name of the original database
        :param db_name: Name of the new database
        :param neutralize: Whether to neutralize the database (default: False)
        :return: True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, db_original_name, db_name, neutralize]
        return self._jsonrpc("db", "duplicate_database", arguments)

    def database_drop(self, master_password, db_name):
        """Drop an Odoo database

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L197-L220

        :param master_password: Master password for the Odoo server
        :param db_name: Name of the database to drop
        :return: True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, db_name]
        return self._jsonrpc("db", "drop", arguments)

    def database_dump(self, master_password, db_name, fmt):
        """Dump an Odoo database

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L223-L227

        :param master_password: Master password for the Odoo server
        :param db_name: Name of the database to dump
        :param format: Format of the dump 'zip' or 'pgdump'
        :return: The database dump as a string (base64 encoded)
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, db_name, fmt]
        # TODO: do we need to tell urllib about the streamed response?
        return self._jsonrpc("db", "dump", arguments, http_method="get")

    def database_restore(self, master_password, db_name, data, copy=False):
        """Restore an Odoo database from a dump

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L282-L294

        :param master_password: Master password for the Odoo server
        :param db_name: Name of the database to restore
        :param data: The database dump data (base64 encoded)
        :param copy: Whether to create a copy of the database (default: False)
        :return: True if the database was restored successfully
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, db_name, data, copy]
        # TODO: do we need to do any special streaming here?
        return self._jsonrpc("db", "restore", arguments)

    def database_rename(self, master_password, old_name, new_name):
        """Rename an Odoo database

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L351-L371

        :param master_password: Master password for the Odoo server
        :param old_name: The current name of the database
        :param new_name: The new name for the database
        :return: True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [old_name, new_name]
        return self._jsonrpc("db", "rename", arguments)

    def database_migrate(self, master_password, databases):
        """Migrate an Odoo database to a new name

        This effectively triggers an upgrade on the 'base' module

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L380-L385

        :param master_password: Master password for the Odoo server
        :param databases: A list of databases to migrate
        :return: True
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, databases]
        return self._jsonrpc("db", "migrate_databases", arguments)

    def database_exists(self, master_password, db_name):
        """Check if a database exists

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L392-L399

        :param master_password: Master password for the Odoo server
        :param db_name: The database name to check
        :return: True if the DB exists, otherwise False
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [
            master_password,
            db_name,
        ]
        return self._jsonrpc("db", "db_exist", arguments)

    def database_list(self, document=False):
        """List the databases available on an Odoo server

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L452C14-L455

        :param document: Seemingly, nothing...
        :return: A list of database names
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [
            document,
        ]
        return self._jsonrpc("db", "list", arguments)

    def database_list_lang(self):
        """List the available languages on an Odoo server

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L457-L458

        :return: A list of language codes (e.g., 'en_NZ', 'en_GB', etc)
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        return self._jsonrpc("db", "list_lang", [])

    def database_list_countries(self, master_password):
        """List the available countries on an Odoo server

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L460-L467

        :param master_password: Master password for the Odoo server
        :return: A list of [code, name] pairs (where `code` is an ISO code, like NZ, GB, etc)
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password]
        return self._jsonrpc("db", "list_countries", arguments)

    def server_version(self):
        """Fetches the server version

        Note: This is technically part of the 'db' service, but it's really a
        general-purpose method, so it can live under "misc".

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L469-L473

        :return: The Odoo version (e.g., "18.0", "saas-16.3", etc)
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        return self._jsonrpc("db", "server_version", [])

    def change_admin_password(self, master_password, new_master_password):
        """Change the admin/master password

        Note: This is technically part of the 'db' service, but it's really a
        general-purpose method, so it can live under "misc".

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/db.py#L374-L377

        :param master_password: Master password for the Odoo server
        :param new_master_password: The new password for the admin user
        :return: True if the password was changed successfully
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        arguments = [master_password, new_master_password]
        return self._jsonrpc("db", "change_admin_password", arguments)

    ### services/model

    def model_execute(self, model, method, args=[]):
        """Execute a model/method, passing positional args only

        References:
         - https://github.com/odoo/odoo/blob/a87602a2/odoo/service/model.py#L62-L68

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param method: The method to call (e.g., 'create' or 'search_read')
        :param args: Optional positional args to pass
        :returns: The result from the remote method call
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        self._check_login()
        if args:
            if not isinstance(args, list):
                args = [args]
        if not args:
            args = []
        arguments = [
            self.database,
            self.uid,
            self.password,
            model,
            method,
            # confusingly, we want args to be *inline* with arguments
            # e.g., [model, method, arg1, arg2, arg3, ...]
            *args,
        ]
        return self._jsonrpc(
            "object",
            "execute",
            arguments,
        )

    def model_execute_kw(self, model, method, args=[], kwargs={}):
        """Execute a model/method, passing positional or keyword args

        References:
         -

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param method: The method to call (e.g., 'create' or 'search_read')
        :param args: Optional positional args (list)
        :param kwargs: Optional keyword args (dict)
        :returns: The result from the remote method call
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        self._check_login()
        if args:
            if not isinstance(args, list):
                args = [args]
        arguments = [
            self.database,
            self.uid,
            self.password,
            model,
            method,
            args or [],
            kwargs or {},
        ]
        return self._jsonrpc(
            "object",
            "execute_kw",
            arguments,
        )

    ### ORM methods

    def search(self, model, domain, offset=0, limit=None, order=None):
        """Search for records matching the given domain

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param domain: Search domain (list of tuples)
        :param offset: Number of records to skip
        :param limit: Maximum number of records to return
        :param order: Sorting order
        :returns: List of record IDs matching the domain
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        args = [domain]
        kwargs = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
        return self.execute_kw(model, "search", args, kwargs)

    def search_read(
        self,
        model,
        domain=None,
        fields=None,
        offset=0,
        limit=None,
        order=None,
        load=None,
    ):
        """Search and read records in one call

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param domain: Search domain (list of tuples)
        :param fields: List of field names to read (None for all fields)
        :param offset: Number of records to skip
        :param limit: Maximum number of records to return
        :param order: Sorting order
        :returns: List of dictionaries containing the record data
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        kwargs = {"offset": offset}
        if domain is not None:
            kwargs["domain"] = domain
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
        if load is not None:
            kwargs["load"] = load or False

        return self.execute_kw(model, "search_read", [], kwargs)

    def create(self, model, values):
        """Create a new record
        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param values: Dictionary containing field values for the new record
        :returns: ID of the created record
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        args = [values]
        return self.execute_kw(model, "create", args)

    def write(self, model, ids, values):
        """Update existing records

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param ids: List of record IDs to update (or single ID)
        :param values: Dictionary containing field values to update
        :returns: True if successful
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        # Ensure ids is a list
        if isinstance(ids, int):
            ids = [ids]

        args = [ids, values]
        return self.execute_kw(model, "write", args)

    def unlink(self, model, ids):
        """Delete records

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param ids: List of record IDs to delete (or single ID)
        :returns: True if successful
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        # Ensure ids is a list
        if isinstance(ids, int):
            ids = [ids]

        args = [ids]
        return self.execute_kw(model, "unlink", args)

    def read(self, model, ids, fields=None, load=None):
        """Read records from a model

        :param model: The Odoo model (e.g., 'res.partner' or 'sale.order')
        :param ids: List of record IDs to read
        :param fields: List of field names to read (None for all fields)
        :param load: Loading mode, pass `False` to avoid computing display_name
        :returns: List of dictionaries containing the record data
        :raises OdooConnectionError: If there is a connection issue
        :raises OdooJsonRpcError: If the JSON-RPC response is invalid
        """
        args = [ids]
        kwargs = {}
        if fields is not None:
            kwargs["fields"] = fields
        if load is not None:
            kwargs["load"] = load or False

        return self.execute_kw(model, "read", args, kwargs)

    ### aliases
    execute = model_execute
    execute_kw = model_execute_kw
