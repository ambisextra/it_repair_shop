# import db functions for creating, updating, and retrieving repair tickets
from src.database import (
    add_repair_ticket,
    update_repair_ticket_status,
    get_repair_ticket,
    get_all_repair_tickets,
    get_repair_ticket_details,
)

# define the permitted repair ticket statuses using a set for efficient membership checks
VALID_STATUSES = {
    "received",
    "diagnosing",
    "waiting_for_parts",
    "repairing",
    "ready",
    "completed",
}

# organize db operations related to repair tickets
class RepairTicketRepository:
    # initialize the repo with an existing db connection
    def __init__(self, connection):
        # store connection for use by other repo methods
        self.connection = connection

    # add a repair ticket using the repo's stored db connection
    def add(self, device_id, issue_description):
        return add_repair_ticket(
            self.connection,
            device_id,
            issue_description,
        )

    # Reject update if requested status is not permitted
    def update_status(self, ticket_id, status):
        if status not in VALID_STATUSES:
            return False
        # Manage the transaction, committing on success or rolling back if exception occurs
        with self.connection:
            # update the ticket status and return whether a row was affected
            return update_repair_ticket_status(
                self.connection,
                ticket_id,
                status,
            )

    # retrieve a repair ticket by ID using db layer
    def get(self, ticket_id):
        return get_repair_ticket(
            self.connection,
            ticket_id,
        )

    # retrieve and return list of all repair tickets
    def get_all(self):
        return get_all_repair_tickets(
            self.connection,
        )

    # retrieve a repair ticket with associated device info and customer details
    def get_details(self, ticket_id):
        return get_repair_ticket_details(
            self.connection,
            ticket_id,
        )