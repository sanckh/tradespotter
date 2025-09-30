"""Database constants and enums for the PTR Ingestion Worker."""

from enum import Enum


class FilingType(str, Enum):
    """Filing type enum matching the database filing_type_enum."""
    
    PTR = "P"  # Periodic Transaction Report
    AMENDMENT = "A"  # Amendment
    CANDIDATE = "C"  # Candidate
    DISCLOSURE = "D"  # Disclosure
    OFFICER = "O"  # Officer
    EXTENSION = "X"  # Extension
    WITHDRAWAL = "W"  # Withdrawal
    
    @classmethod
    def get_description(cls, filing_type: str) -> str:
        """Get human-readable description for filing type."""
        descriptions = {
            cls.PTR: "Periodic Transaction Report",
            cls.AMENDMENT: "Amendment",
            cls.CANDIDATE: "Candidate",
            cls.DISCLOSURE: "Disclosure",
            cls.OFFICER: "Officer",
            cls.EXTENSION: "Extension",
            cls.WITHDRAWAL: "Withdrawal"
        }
        return descriptions.get(filing_type, filing_type)
    
    @classmethod
    def is_valid(cls, filing_type: str) -> bool:
        """Check if filing type is valid."""
        return filing_type in [ft.value for ft in cls]


# Mapping used by TXT parser (already exists in txt_parser.py)
FILING_TYPE_MAP = {
    'A': 'Amendment',
    'C': 'Candidate',
    'D': 'Disclosure',
    'O': 'Officer',
    'P': 'Periodic Transaction Report',
    'X': 'Extension',
    'W': 'Withdrawal'
}
