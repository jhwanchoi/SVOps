class DomainException(Exception):
    pass


class EntityNotFound(DomainException):
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")


class EntityAlreadyExists(DomainException):
    def __init__(self, entity_type: str, field: str, value: str):
        self.entity_type = entity_type
        self.field = field
        self.value = value
        super().__init__(f"{entity_type} with {field}='{value}' already exists")


class ValidationError(DomainException):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error for {field}: {message}")


class UnauthorizedError(DomainException):
    pass


class ForbiddenError(DomainException):
    pass