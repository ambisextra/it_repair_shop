from src.database import (
    add_repair_ticket,
    update_repair_ticket_status,
    get_repair_ticket,
    get_all_repair_tickets,
    get_repair_ticket_details,
)

VALID_STATUSES = {
    "recieved",
    "diagnosing",
    "waiting_for_parts",
    "repairing",
    "ready",
    "completed",
}

class RepairTicketRepository:
    def __init__(self, connection):
        self.connection = connection

    def add(self, device_id, issue_description):
        return add_repair_ticket(
            self.connection,
            device_id,
            issue_description,
        )

    def update_status(self, ticket_id, status):
        if status not in VALID_STATUSES:
            return False
        with self.connection:
            return update_repair_ticket_status(
                self.connection,
                ticket_id,
                status,
            )

    def get(self, ticket_id):
        return get_repair_ticket(
            self.connection,
            ticket_id,
        )

    def get_all(self):
        return get_all_repair_tickets(
            self.connection,
        )

    def get_details(self, ticket_id):
        return get_repair_ticket_details(
            self.connection,
            ticket_id,
        )