from src.database import (
    add_diagnostic,
    update_repair_ticket_status,
)

def begin_diagnosis(connection, ticket_id, notes):
    with connection:
        add_diagnostic(
            connection,
            ticket_id,
            notes,
        )
        updated = update_repair_ticket_status(
            connection,
            ticket_id,
            "diagnosing",
        )
        if not updated:
            raise ValueError("Repair ticket not found")
    return True