"""Safe domain findings shared by normalization, compilation and HTTP clients."""


class DomainError(ValueError):
    def __init__(self, findings: list[dict]):
        self.findings = findings
        first = findings[0] if findings else {}
        self.code = first.get("code", "DOMAIN_INVALID")
        self.field = first.get("field", "")
        self.details = first.get("details", {})
        self.message = first.get("message", "Invalid project.")
        super().__init__(self.message)


def finding(code: str, message: str, field: str, **details) -> dict:
    return {"code": code, "message": message, "field": field, "details": details}
