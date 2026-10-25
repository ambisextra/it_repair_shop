# import db functions for adding diagnostic notes and updating repair ticket statuses
from src.database import (
    add_diagnostic,
    update_repair_ticket_status,
)

# add diagnostic notes and change a ticket's status as part of one db transaction
def begin_diagnosis(connection, ticket_id, notes):
    # commit both operations on success or roll back on failure
    with connection:
        # insert diagnostic notes associated with the specified repair ticket
        add_diagnostic(
            connection,
            ticket_id,
            notes,
        )
        # attempt to change ticket status to "dianosing" and store whether update affected a record
        updated = update_repair_ticket_status(
            connection,
            ticket_id,
            "diagnosing",
        )
        # raise an exception if no ticket was updated, causing the transaction to roll back
        if not updated:
            raise ValueError("Repair ticket not found")
    # true after both db operations succeeded and transaction has committed
    return True