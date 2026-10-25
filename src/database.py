import sqlite3
from pathlib import Path

def create_connection(db_path):
    path = Path(db_path)    # converts database file location into Path object
    connection = sqlite3.connect(path)  # open sqlite database and store connection object
    connection.row_factory = sqlite3.Row    # allows results to be accessed by column name
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def create_customers_table(connection):
    # create the customers table only if it doesn't exist
    sql = """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT
    )
    """
    connection.execute(sql)
    connection.commit() # commits pending transaction changes

def initialize_database(db_path):
    connection = create_connection(db_path) # open the database and obtain a configured sqlite connection
    # create database tables for customers, devices, tickets, & records
    create_customers_table(connection)
    create_devices_table(connection)
    create_repair_tickets_table(connection)
    create_diagnostics_table(connection)
    # create triggers that prevent invalid repair ticket statuses
    create_repair_ticket_status_triggers(connection)
    run_migrations(connection)  # apply database schema changes that haven't been installed yet
    return connection   # returns initialized db connection for use by app

# add a customer, phone and email can be ommitted
def add_customer(connection, name, phone=None, email=None):
    # insert a customer using parameterized sql to safely supply values
    # use sql placeholders to bind customer values and prevent user input from being interpreted as sql
    cursor = connection.execute(
        """
        INSERT INTO customers (
            name,
            phone,
            email
        )
        VALUES (?, ?, ?)
        """,
        (name, phone, email)
    )
    connection.commit() # save new customer record to database
    return cursor.lastrowid # return unique id assigned to new customer

def create_devices_table(connection):
    sql = """
    CREATE TABLE IF NOT EXISTS devices (
        device_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        device_type TEXT NOT NULL,
        manufacturer TEXT,
        model TEXT,
        serial_number TEXT,
        FOREIGN KEY (customer_id)
            REFERENCES customers(customer_id)
    )
    """
    connection.execute(sql) # execute sql statement using database conneciton
    connection.commit() # commit any pending db changes

# add a device associated with a customer, allowing device identification details
def add_device(
        connection,
        customer_id,
        device_type,
        manufacturer=None,
        model=None,
        serial_number=None,
):
    # insert device info using parameterized sql. associate device with an existing customer
    cursor = connection.execute (
        """
        INSERT INTO devices (
            customer_id,
            device_type,
            manufacturer,
            model,
            serial_number
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            customer_id,
            device_type,
            manufacturer,
            model,
            serial_number,
        ),
    )
    connection.commit() # commit new device record
    return cursor.lastrowid # return ID assigned to newly inserted device

def create_repair_tickets_table(connection):
    sql = """
    CREATE TABLE IF NOT EXISTS repair_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        issue_description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'received',
        FOREIGN KEY (device_id)
            REFERENCES devices(device_id)
        )
        """
    connection.execute(sql)
    connection.commit()

# create a new repair ticket for an existing device and return a new ticket ID
def add_repair_ticket(
        connection,
        device_id,
        issue_description,
):
    # insert a repair ticket and store cursor to retrieve new ticket ID
    cursor = connection.execute(
        """
        INSERT INTO repair_tickets (
            device_id,
            issue_description
        )
        VALUES (?, ?)
        """,
        (
            device_id,
            issue_description,
        )
    )
    connection.commit()
    return cursor.lastrowid

# update the status of existing repair ticket using ticket ID
def update_repair_ticket_status(connection, ticket_id, status):
    cursor = connection.execute(
        """
        UPDATE repair_tickets
        SET status = ?
        WHERE ticket_id = ?
        """,
        (
            status,
            ticket_id,
        ),
    )
    # return T if at least one ticket was updated
    # return whether a ticket was updated
    return cursor.rowcount > 0

def get_repair_ticket(connection, ticket_id):
    cursor = connection.execute(
        """
        SELECT
            ticket_id,
            device_id,
            issue_description,
            status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    )
    # return the matching repair ticket by unique ID
    return cursor.fetchone()

# retrieves all repair tickets ordered by ticket ID
def get_all_repair_tickets(connection):
    cursor = connection.execute(
        """
        SELECT
            ticket_id,
            device_id,
            issue_description,
            status
        FROM repair_tickets
        ORDER BY ticket_id
        """
    )
    # return all repair tickets as a list of db rows
    return cursor.fetchall()

def get_repair_ticket_details(connection, ticket_id):
    # join repair tickets with their devices and customer to retrieve complete repair info
    cursor = connection.execute(
        """
        SELECT
            repair_tickets.ticket_id,
            repair_tickets.issue_description,
            repair_tickets.status,
            devices.device_type,
            devices.manufacturer,
            devices.model,
            devices.serial_number,
            -- rename the customers name column in query results
            customers.name AS customer_name,
            customers.phone,
            customers.email
        FROM repair_tickets
        JOIN devices
            ON repair_tickets.device_id = devices.device_id
        JOIN customers
            ON devices.customer_id = customers.customer_id
        WHERE repair_tickets.ticket_id = ?
        """,
        (ticket_id,),
    )
    # return matching ticket with its joined customer and device details
    return cursor.fetchone()

def create_diagnostics_table(connection):
    sql = """
    CREATE TABLE IF NOT EXISTS diagnostics (
        diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- require a repair ticket ID and diagnostic notes
        ticket_id INTEGER NOT NULL,
        notes TEXT NOT NULL,
        -- associate each diagnostic record with an existing repair ticket
        FOREIGN KEY (ticket_id)
            REFERENCES repair_tickets(ticket_id)
    )
    """
    connection.execute(sql) # execute sql to create diagnostic table
    connection.commit() # commit any pending db changes

# add a diagnostic note associated with existing repair ticket
def add_diagnostic(connection, ticket_id, notes,):
    cursor = connection.execute(
        """
        INSERT INTO diagnostics (
            ticket_id,
            notes
        )
        VALUES (?, ?)
        """,
        (
            ticket_id,
            notes,
        ),
    )
    # return ID assigned to newly inserted diagnostic record
    return cursor.lastrowid

def create_repair_ticket_status_triggers(connection):
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS validate_repair_ticket_status_insert
        BEFORE INSERT ON repair_tickets
        -- check whether the new status is outside the list of allowed statuses
        WHEN NEW.status NOT IN (
            'received',
            'diagnosing',
            'waiting_for_parts',
            'repairing',
            'ready',
            'completed'
        )
        BEGIN
            -- abort sql statement if repair status is invalid
            SELECT RAISE(
                ABORT,
                'invalid repair ticket status'
            );
        END;
        """
    )
    connection.execute(
        """
        -- validate new status before existing ticket is updated
        CREATE TRIGGER IF NOT EXISTS validate_repair_ticket_status_update
        BEFORE UPDATE OF status ON repair_tickets
        WHEN NEW.status NOT IN (
            'received',
            'diagnosing',
            'waiting_for_parts',
            'repairing',
            'ready',
            'completed'
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'invalid repair ticket status'
            );
        END;
        """
    )
    connection.commit()

# retrieve the current db schema version
def get_database_version(connection):
    row = connection.execute(
        "PRAGMA user_version"
    ).fetchone()
    return row[0]

# update sqlite's stored schema version number
def set_database_version(connection, version):
    connection.execute(
        f"PRAGMA user_version = {version}"
    )

def run_migrations(connection):
    # retrieve current schema version before applying migrations
    version = get_database_version(connection)
    # establish schema verison 1 if db is not yet versioned
    if version < 1:
        with connection:
            set_database_version(connection, 1)
        version = 1
    # add a priority column to existing repair tickets and advance schema to version 2, apply migration 2 and record updated schema version
    if version < 2:
        with connection:
            # starts transaction so schema change and version update suceed or fail together
            connection.execute("BEGIN")
            connection.execute(
                """
                ALTER TABLE repair_tickets
                ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'
                """
            )
            set_database_version(connection, 2)
        version = 2
    # create an index on device_id to improve repair ticket lookups, update db schema to 3
    if version < 3:
        with connection:
            # starts a transaction so the index creation and schema version update either both succeed or both roll back
            connection.execute("BEGIN")
            connection.execute(
                """
                CREATE INDEX idx_repair_tickets_device_id
                ON repair_tickets(device_id)
                """
            )
            set_database_version(connection, 3)
        version = 3