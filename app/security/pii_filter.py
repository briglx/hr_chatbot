"""Module for filtering personally identifiable information (PII) from text."""


class PIIFilter:
    """Utility class for filtering personally identifiable information (PII) from text."""

    def __init__(self) -> None:
        """Initialize the PIIFilter with a list of keywords that are commonly associated with PII. This is a simple heuristic approach; in a production system, you would likely want to use a more robust method for detecting PII."""
        # In a production system, this might be backed by a more comprehensive PII detection library or service.
        self._pii_keywords = [
            "email",
            "phone",
            "address",
            "ssn",
            "social security number",
        ]

    def filter(self, text: str) -> str:
        """Redact any detected PII from the input text."""
        redacted_text = text
        for keyword in self._pii_keywords:
            if keyword in redacted_text.lower():
                redacted_text = redacted_text.replace(keyword, "[REDACTED]")
        return redacted_text
