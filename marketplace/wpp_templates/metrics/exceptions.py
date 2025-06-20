class TemplateMetricsException(Exception):
    """Raised when expected errors occur in the template metrics use case."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
