"""
Shared Pytest Fixtures for DevTalenty AI Extractor.

This module provides mocks and dummy payloads to isolate tests from
external I/O (Database, Groq/OpenAI, and File System).
"""

import pytest


@pytest.fixture
def mock_upload_file_content() -> bytes:
    """Simulates the binary bytes of an uploaded PDF."""
    return b"%PDF-1.4 mock content for unit tests"


@pytest.fixture
def mock_groq_llm_payload() -> dict:
    """
    Simulates the JSON dictionary that Groq/instructor returns
    when extracting a CandidateProfile successfully.
    """
    return {
        "full_name": "Dylan M",
        "email": "dylan@example.com",
        "phone": "+1234567890",
        "location": "Remote",
        "professional_summary": "Senior QA Engineer",
        "skills": ["Python", "Pytest", "FastAPI"],
        "years_of_experience": 5,
        "work_experience": [
            {
                "job_title": "QA Engineer",
                "company": "Tech Corp",
                "duration": "2020-2023",
                "description": "Automated testing.",
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "University of Tech",
                "year": "2020",
            }
        ],
        "languages": ["English", "Spanish"],
    }
