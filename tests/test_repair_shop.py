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
import sqlite3
import pytest

def test_initialize_database_creates_customers_table():
    connection = initialize_database(":memory:")
    table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name = 'customers'
        """
    ).fetchone()
    assert table is not None
    connection.close()

def test_add_customer():
    connection = initialize_database(":memory:")
    customer_id = add_customer(
        connection,
        "Marcus Hinton",
        "480-289-1629",
        "marchinton@gmail.com",
    )
    customer = connection.execute(
        """
        SELECT customer_id, name, phone, email
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,),
    ).fetchone()
    assert customer["name"] == "Marcus Hinton"
    assert customer["phone"] == "480-289-1629"
    assert customer["email"] == "marchinton@gmail.com"
    connection.close()

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
    assert device["customer_id"] == customer_id
    assert device["device_type"] == "Laptop"
    assert device["manufacturer"] == "Lenovo"
    assert device["model"] == "ThinkPad T14"
    assert device["serial_number"] == "SN123456"
    connection.close()

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
    connection.rollback()
    ticket = connection.execute(
        """
        SELECT status
        FROM repair_tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    assert ticket["status"] == "received"
    connection.close()

def test_database_schema_version_is_2():
    connection = initialize_database(":memory:")
    version = get_database_version(connection)
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
    assert "priority" in column_names
    connection.close()

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
    assert len(priority_columns) == 1
    connection.close()

def test_failed_migration_rolls_back():
    connection = initialize_database(":memory:")
    original_version = get_database_version(connection)
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
        connection.close()

def test_migration_3_creates_index(tmp_path):
    db_path = tmp_path / "repair_shop.db"
    connection = initialize_database(db_path)
    try:
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