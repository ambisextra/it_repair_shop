from src.database import (
    initialize_database,
    add_customer,
    add_device,
    add_repair_ticket,
    update_repair_ticket_status,
    add_diagnostic,
    get_database_version,
    set_database_version,
    run_migrations,
)
from src.repair_ticket_repository import RepairTicketRepository
from src.repair_service import begin_diagnosis
# import sqlite support and the pytest testing framework
import sqlite3
import pytest

# verify that db initialization creates customers table
def test_initialize_database_creates_customers_table():
    # create a temp sqlite db in memory for testing
    connection = initialize_database(":memory:")
    # check sqlite's schema metadata for the customers table
    table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'customers'
        """
    ).fetchone()
    # verify that the customers table was successfully created
    assert table is not None
    # close the sqlite connection and release its resources
    connection.close()

# verify that a customer can be inserted and retrieved correctly
def test_add_customer():
    # initialize an isolated in-memory db
    connection = initialize_database(":memory:")
    # insert a test customer and capture the generated ID
    customer_id = add_customer(
        connection,
        "Marcus Hinton",
        "480-745-0086",
        "marchinton@gmail.com",
    )
    # retrieve the newly inserted customer using their unique ID
    customer = connection.execute(
        """
        SELECT customer_id, name, phone, email
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,),
    ).fetchone()
    # verify that the retrieved customer info matches the values originally inserted
    assert customer["name"] == "Marcus Hinton"
    assert customer["phone"] == "480-745-0086"
    assert customer["email"] == "marchinton@gmail.com"
    connection.close()

# verify that db initialization creates the devices table
def test_initalize_database_creates_devicers_table():
    connection = initialize_database(":memory:")
    table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'devices'
        """
    ).fetchone()
    assert table is not None
    connection.close()

def test_add_device():
    connection = initialize_database(":memory:")
    # create a customer first so the new device can reference an existing customer ID
    customer_id = add_customer(
        connection,
        "Poopy Butthole",
        "480-555-0761",
        "poopybutt69@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Lenovo",
        "ThinkPad T14",
        "SN123456"
    )
    device = connection.execute(
        """
        SELECT
            device_id,
            customer_id,
            device_type,
            manufacturer,
            model,
            serial_number
        FROM devices
        WHERE device_id = ?
        """,
        (device_id,),
    ).fetchone()
    # verify the device belongs to the correct customer and its identifying info was stored correctly
    assert device["customer_id"] == customer_id
    assert device["device_type"] == "Laptop"
    assert device["manufacturer"] == "Lenovo"
    assert device["model"] == "ThinkPad T14"
    assert device["serial_number"] == "SN123456"
    connection.close()

# verify that db initialization creates the repair_tickets table
def test_initialize_database_creates_repair_tickets_table():
    connection = initialize_database(":memory:")
    table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'repair_tickets'
        """
    ).fetchone()
    assert table is not None
    connection.close()

# verify the ticket is associated with correct device, contains the reported issue, and has default status
def test_add_repair_ticket():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Clip Clop",
        "602-555-0395",
        "clipping4u@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Desktop",
        "Dell",
        "OptiPlex 7090",
        "SN987654",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "Computer will not boot",
    )
    ticket = connection.execute(
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
    ).fetchone()
    assert ticket["device_id"] == device_id
    assert ticket["issue_description"] == "Computer will not boot"
    assert ticket["status"] == "received"
    connection.close()

def test_update_repair_ticket_status():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Lester Crinklesack",
        "602-394-0034",
        "less4less@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Apple",
        "MacBook Pro",
        "SN555111",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "Battery not charging",
    )
    success = update_repair_ticket_status(
        connection,
        ticket_id,
        "diagnosing",
    )
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    # verify that the update affected a ticket and the new status was stored correctly
    assert success is True
    assert ticket["status"] == "diagnosing"
    connection.close()

def test_repair_ticket_repository_rejects_invalid_status():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Eve Carter",
        "623-884-8392",
        "evecarter@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Desktop",
        "HP",
        "EliteDesk",
        "SN222333",
    )
    repository = RepairTicketRepository(connection)
    ticket_id = repository.add(
        device_id,
        "Random shutdowns",
    )
    success = repository.update_status(
        ticket_id,
        "broken_status",
    )
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    # verify that invalid repair statuses are rejected without modifying the existing ticket
    assert success is False
    assert ticket["status"] == "received"
    connection.close()

def test_repair_ticket_repository_get():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Frank Miller",
        "480-220-0113",
        "frankmiller@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Dell",
        "Latitude 7420",
        "SN444555",
    )
    repository = RepairTicketRepository(connection)
    ticket_id = repository.add(
        device_id,
        "Keyboard not responding",
    )
    # verify the ticket exists and its stored values match info used to create it
    ticket = repository.get(ticket_id)
    assert ticket is not None
    assert ticket["ticket_id"] == ticket_id
    assert ticket["device_id"] == device_id
    assert ticket["issue_description"] == "Keyboard not responding"
    assert ticket["status"] == "received"
    connection.close()

def test_repair_ticket_repository_get_all():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Grace Hall",
        "602-448-1193",
        "gracehall@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Lenovo",
        "ThinkPad X1",
        "SN777888",
    )
    repository = RepairTicketRepository(connection)
    repository.add(
        device_id,
        "Screen flickering",
    )
    repository.add(
        device_id,
        "USB port not working",
    )
    # verify that both repair tickets were retrieved in expected order with correct descriptions
    tickets = repository.get_all()
    assert len(tickets) == 2
    assert tickets[0]["issue_description"] == "Screen flickering"
    assert tickets[1]["issue_description"] == "USB port not working"
    connection.close()

def test_repair_ticket_repository_get_details():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Helen Brooks",
        "480-935-1194",
        "helenbrooks@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Apple",
        "MacBook Air",
        "SN999000",
    )
    repository = RepairTicketRepository(connection)
    ticket_id = repository.add(
        device_id,
        "Trackpad not clicking",
    )
    # verify that the joined query returns the correct repair ticket, device, and customer info
    details = repository.get_details(ticket_id)
    assert details["ticket_id"] == ticket_id
    assert details["issue_description"] == "Trackpad not clicking"
    assert details["status"] == "received"
    assert details["device_type"] == "Laptop"
    assert details["manufacturer"] == "Apple"
    assert details["model"] == "MacBook Air"
    assert details["serial_number"] == "SN999000"
    assert details["customer_name"] == "Helen Brooks"
    assert details["phone"] == "480-935-1194"
    assert details["email"] == "helenbrooks@gmail.com"
    connection.close()

# verify that db init creates the diagnostics table
def test_initialize_database_creates_diagnostics_table():
    connection = initialize_database(":memory:")
    table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'diagnostics'
        """
    ).fetchone()
    assert table is not None
    connection.close()

def test_add_diagnostic():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Ian Parker",
        "602-901-4455",
        "ianparker@gmail.com"
    )
    device_id = add_device(
        connection,
        customer_id,
        "Desktop",
        "Dell",
        "Precision 3660",
        "SN123789",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "Computer randomly freezes",
    )
    diagnostic_id = add_diagnostic(
        connection,
        ticket_id,
        "SSD failing SMART test",
    )
    diagnostic = connection.execute(
        """
        SELECT diagnostic_id, ticket_id, notes
        FROM diagnostics
        WHERE diagnostic_id = ?
        """,
        (diagnostic_id,),
    ).fetchone()
    # verify the diag belongs to the correct ticket and that its notes were stored accurately
    assert diagnostic["ticket_id"] == ticket_id
    assert diagnostic["notes"] == "SSD failing SMART test"
    connection.close()

def test_begin_diagnosis_success():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Jane Cooper",
        "623-762-1109",
        "janecooper@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Lenovo",
        "ThinkPad T14",
        "SN555999",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "Laptop shuts down under load",
    )
    result = begin_diagnosis(
        connection,
        ticket_id,
        "CPU overheating during stress test",
    )
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    diagnostic = connection.execute(
        """
        SELECT notes
        FROM diagnostics
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    # verify the diag workflow succeeded, updated the ticket status, and saved the diag notes
    assert result is True
    assert ticket["status"] == "diagnosing"
    assert diagnostic["notes"] == "CPU overheating during stress test"
    connection.close()

def test_begin_diagnosis_rolls_back_on_status_failure():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Rollback Customer",
        "480-999-9999",
        "rollback@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "Dell",
        "Latitude 5430",
        "SNROLL001",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "System crashes randomly",
    )
    connection.execute(
        f"""
        CREATE TRIGGER force_status_failure
        BEFORE UPDATE ON repair_tickets
        WHEN NEW.ticket_id = {ticket_id}
        BEGIN
            SELECT RAISE(ABORT, 'forced status failure');
        END;
        """
    )
    connection.commit()
    # verify that a forced status-update failure raises the expected sqlite integrity error
    with pytest.raises(sqlite3.IntegrityError):
        begin_diagnosis(
            connection,
            ticket_id,
            "Diagnostic should be rolled back",
        )
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    # verify the failed transaction preserved the original ticket status and rolled back the diagnostic insertion
    assert ticket["status"] == "received"
    diagnostic = connection.execute(
        """
        SELECT diagnostic_id
        FROM diagnostics
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    assert diagnostic is None
    connection.close()

def test_database_rejects_invalid_repair_ticket_status():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Status Test Customer",
        "480-821-3456",
        "status@gmail.com",
    )
    device_id = add_device(
        connection,
        customer_id,
        "Laptop",
        "HP",
        "EliteBook",
        "SNSTATUS001",
    )
    ticket_id = add_repair_ticket(
        connection,
        device_id,
        "Testing status validation",
    )
    # verify the db trigger rejects invalid statuses and raises the expected integrity error
    with pytest.raises(
        sqlite3.IntegrityError, match="invalid repair ticket status",
    ):
        connection.execute(
            """
            UPDATE repair_tickets
            SET status = ?
            WHERE ticket_id = ?
            """,
            (
                "not_a_real_status",
                ticket_id,
            ),
        )
    # roll back any uncommitted db changes
    connection.rollback()
    # retrieve the ticket after the rejected update
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    # verify the ticket retians its original status
    assert ticket["status"] == "received"
    # close the db connection
    connection.close()

# verify that db init applies migrations through version 3
def test_database_schema_version_is_3():
    connection = initialize_database(":memory:")
    # retrieve the current db schema version
    version = get_database_version(connection)
    # confirm the schema is at version 3
    assert version == 3
    connection.close()

def test_priority_column_exists_after_migration():
    connection = initialize_database(":memory:")
    columns = connection.execute(
        """
        PRAGMA table_info(repair_tickets)
        """
    ).fetchall()
    column_names = [
        column["name"]
        for column in columns
    ]
    # verify that migration 2 added the priority column by examining the repair_tickets table structure
    assert "priority" in column_names
    connection.close()

# verify that rerunning migrations does not duplicate schema changes or alter the current db version
def test_migrations_are_idempotent():
    connection = initialize_database(":memory:")
    run_migrations(connection)
    run_migrations(connection)
    version = get_database_version(connection)
    columns = connection.execute(
        """
        PRAGMA table_info(repair_tickets)
        """
    ).fetchall()
    priority_columns = [
        column
        for column in columns
        if column["name"] == "priority"
    ]
    assert version == 3
    # filter table's column metadata to find columns named "priority" and verify exactly one exists
    assert len(priority_columns) == 1
    connection.close()

# verify that a failed migration rolls back db schema changes
def test_failed_migration_rolls_back():
    connection = initialize_database(":memory:")
    original_version = get_database_version(connection)
    # expect an OperationalError from invalid sql to test how to db handles a failed migration
    try:
        with pytest.raises(sqlite3.OperationalError):
            with connection:
                connection.execute(
                    """
                    CREATE TABLE migration_test (
                        id INTEGER PRIMARY KEY
                    )
                    """
                )
                connection.execute(
                    """
                    THIS IS INVALID SQL
                    """
                )
                set_database_version(connection, 99)
            # verify the failed migration was rolled back
            table = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                    AND name = 'migration_test'
                """
            ).fetchone()
            assert table is None
            assert get_database_version(connection) == original_version
    finally:
        connection.close()

# verify migration 3 updates the schema version and creates the index on repair_tickets.device_id
def test_migration_3_creates_index(tmp_path):
    db_path = tmp_path / "repair_shop.db"
    connection = initialize_database(db_path)
    try:
        # verify the db version and index
        version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
        assert version == 3
        indexes = connection.execute(
            "PRAGMA index_list('repair_tickets')"
        ).fetchall()
        index_names = [row["name"] for row in indexes]
        assert "idx_repair_tickets_device_id" in index_names
    finally:
        connection.close()

def test_repair_ticket_query_uses_index(tmp_path):
    db_path = tmp_path / "repair_shop.db"
    connection = initialize_database(db_path)
    try:
        # examine sqlite's execution plan for finding repair tickets associated with a device
        plan = connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM repair_tickets
            WHERE device_id = ?
            """,
            (1,),
        ).fetchall()
        for row in plan:
            print(row["detail"])
        # verify that sqlite plans to use the device_id index
        assert any(
            "idx_repair_tickets_device_id" in row["detail"]
            for row in plan
        )
    finally:
        connection.close()

def test_compare_index_vs_table_scan(tmp_path):
    db_path = tmp_path / "repair_shop.db"
    connection = initialize_database(db_path)
    # compare sqlite's query execution plans when indexes are allowed when indexes are allowed versus when index usage is disabled
    try:
        indexed = connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM repair_tickets
            WHERE device_id = ?
            """,
            (1,),
        ).fetchall()
        without_index = connection.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM repair_tickets NOT INDEXED
            WHERE device_id = ?
            """,
            (1,),
        ).fetchall()
        print("\nWITH INDEX:")
        for row in indexed:
            print(row["detail"])
        print("\nWITHOUT INDEX:")
        for row in without_index:
            print(row["detail"])
    finally:
        connection.close()

# create 15 test customers using a loop and generate unique names with an f-string
def test_small_shop_device_history(tmp_path):
    db_path = tmp_path / "small_shop.db"
    connection = initialize_database(db_path)
    try:
        target_device_id = None
        with connection:
            for i in range(15):
                # create a customer, then use their generated ID to associate a new laptop with that customer. store the new device ID for later repair tickets
                customer = connection.execute(
                    "INSERT INTO customers (name) VALUES (?)",
                    (f"Customer {i}",)
                )
                device = connection.execute(
                    """
                    INSERT INTO devices
                    (customer_id, device_type)
                    VALUES (?, ?)
                    """,
                    (customer.lastrowid, "Laptop")
                )
                device_id = device.lastrowid
                # save the fourth customer's device ID so we can verify its repair history later
                if i == 3:
                    target_device_id = device_id
                connection.execute(
                    """
                    INSERT INTO repair_tickets
                    (device_id, issue_description)
                    VALUES (?, ?)
                    """,
                    (device_id, "Battery replacement")
                )
                # every third customer returns for another repair
                if i % 3 == 0:
                    connection.execute(
                        """
                        INSERT INTO repair_tickets
                        (device_id, issue_description)
                        VALUES (?, ?)
                        """,
                        (device_id, "Charging problem")
                    )
        tickets = connection.execute(
            """
            SELECT *
            FROM repair_tickets
            WHERE device_id = ?
            ORDER BY ticket_id
            """,
            (target_device_id,)
        ).fetchall()
        # verify exactly two repair tickets exist and both belong to the selected device
        assert len(tickets) == 2
        assert all(
            ticket["device_id"] == target_device_id
            for ticket in tickets
        )
        # verify that the first and second repair tickets have the expected issue descriptions in the correct order
        assert tickets[0]["issue_description"] == "Battery replacement"
        assert tickets[1]["issue_description"] == "Charging problem"
    finally:
        connection.close()