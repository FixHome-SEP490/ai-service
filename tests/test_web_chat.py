"""The page the service serves about itself.

Thin on purpose: the behaviour lives in a browser and cannot be asserted from
here. What can be asserted is that the page ships and is wired to the right
endpoints, because the way it breaks is not a wrong pixel — it is a file that
did not make it into the image, or a path that moved.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_the_page_is_served_at_chat(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_the_page_calls_the_endpoints_that_exist(client):
    """A moved path is invisible until someone opens the page and types."""
    body = client.get("/chat").text
    for path in ["/api/v1/diagnosis/analyze-upload", "/api/v1/chat/ask",
                 "/api/v1/chat/acknowledgements"]:
        assert path in body, path
        assert client.get("/openapi.json").json()["paths"].get(path) is not None


def test_the_page_keeps_what_the_owner_asked_it_to_keep(client):
    """Three things were asked for by name: the photograph stays visible, every
    reply stays on screen, and there is a button to start over."""
    body = client.get("/chat").text
    assert "Phiên chat mới" in body
    assert "readAsDataURL" in body
    assert "state.turns.push" in body


def test_the_page_shows_no_internal_document_titles(client):
    """A customer saw "Nguồn: Kịch bản hội thoại mẫu · Cây hỏi, khi chỉ được hỏi
    tối đa hai câu" under an answer about cleaning intervals.

    Citations are how the team checks an answer was grounded. To a customer
    they are the names of files they cannot read, and they say only that
    somebody left the machinery open. They stay in the API response.
    """
    body = client.get("/chat").text
    assert "Nguồn:" not in body
    # The field itself, not the word: the page explains in a comment why it
    # does not render these, and an assertion that forbids the word forbids
    # saying why.
    assert "titleVi" not in body
    assert "r.citations" not in body
