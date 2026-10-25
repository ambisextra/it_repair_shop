class CustomerRepository:
    def __init__(self, connection):
        self.connection = connection
    def find_by_phone(self, phone):