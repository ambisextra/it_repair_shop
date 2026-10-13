import sqlite3
from pathlib import Path

def create_connection(db_path):
    path = Path(db_path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def create_customers_table(connection):
    sql = """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT
    )
    """
    connection.execute(sql)
    connection.commit()

def initialize_database(db_path):
    connection = create_connection(db_path)
    create_customers_table(connection)
    create_devices_table(connection)
    create_repair_tickets_table(connection)
    create_diagnostics_table(connection)
    create_repair_ticket_status_triggers(connection)
    run_migrations(connection)
    return connection

def add_customer(connection, name, phone=None, email=None):
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
    connection.commit()
    return cursor.lastrowid

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
    connection.execute(sql)
    connection.commit()

def add_device(
        connection,
        customer_id,
        device_type,
        manufacturer=None,
        model=None,
        serial_number=None,
):
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
    connection.commit()
    return cursor.lastrowid

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

def add_repair_ticket(
        connection,
        device_id,
        issue_description,
):
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
    return cursor.fetchone()

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
    return cursor.fetchall()

def get_repair_ticket_details(connection, ticket_id):
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
    return cursor.fetchone()

def create_diagnostics_table(connection):
    sql = """
    CREATE TABLE IF NOT EXISTS diagnostics (
        diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        notes TEXT NOT NULL,
        FOREIGN KEY (ticket_id)
            REFERENCES repair_tickets(ticket_id)
    )
    """
    connection.execute(sql)
    connection.commit()

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
    return cursor.lastrowid

def create_repair_ticket_status_triggers(connection):
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS validate_repair_ticket_status_insert
        BEFORE INSERT ON repair_tickets
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
    connection.execute(
        """
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

def get_database_version(connection):
    row = connection.execute(
        "PRAGMA user_version"
    ).fetchone()
    return row[0]

def set_database_version(connection, version):
    connection.execute(
        f"PRAGMA user_version = {version}"
    )

def run_migrations(connection):
    version = get_database_version(connection)
    if version < 1:
        with connection:
            set_database_version(connection, 1)

def run_migrations(connection):
    version = get_database_version(connection)
    if version < 1:
        with connection:
            set_database_version(connection, 1)
        version = 1
    if version < 2:
        with connection:
            connection.execute(
                """
                ALTER TABLE repair_tickets
                ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'
                """
            )
            set_database_version(connection, 2)
        version = 2
    if version < 3:
        with connection:
            connection.execute(
                """
                CREATE INDEX idx_repair_tickets_device_id
                ON repair_tickets(device_id)
                """
            )
            set_database_version(connection, 3)
        version = 3