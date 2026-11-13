"""
The public CV upload is the multipart endpoint anyone on the internet can
reach, so it is the one that has to keep parsing form bodies correctly, and
keep refusing abusive ones, across FastAPI / Starlette / python-multipart
upgrades. S3 is stubbed out.
"""
import pytest

from api.routers import recruitment as recruitment_router

PDF = b"%PDF-1.4\n%test\n"


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    recruitment_router._hits.clear()
    yield
    recruitment_router._hits.clear()


@pytest.fixture
def stored(monkeypatch):
    """What reached S3: a list of (key, bytes, content type)."""
    saved = []

    def upload(fileobj, key, content_type=None):
        saved.append((key, fileobj.read(), content_type))
        return key

    monkeypatch.setattr(recruitment_router.s3_service, "upload_file_to_s3_from_bytes", upload)
    return saved


def test_a_pdf_is_parsed_and_stored(client, stored):
    response = client.post("/recruitment/uploads", files={"file": ("my cv.pdf", PDF, "application/pdf")})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filename"] == "my cv.pdf"
    assert body["s3_key"].startswith("recruitment/") and body["s3_key"].endswith("_my cv.pdf")
    assert stored == [(body["s3_key"], PDF, "application/pdf")]


def test_extra_form_fields_dont_disturb_the_file(client, stored):
    response = client.post(
        "/recruitment/uploads",
        data={"note": "ignored", "another": "also ignored"},
        files={"file": ("cv.pdf", PDF, "application/pdf")},
    )

    assert response.status_code == 200, response.text
    assert stored[0][1] == PDF


def test_a_path_in_the_filename_is_flattened(client, stored):
    response = client.post("/recruitment/uploads", files={"file": ("../../etc/passwd.pdf", PDF, "application/pdf")})

    assert response.status_code == 200, response.text
    assert "/" not in response.json()["filename"]


def test_unsupported_type_is_refused(client, stored):
    response = client.post("/recruitment/uploads", files={"file": ("page.html", b"<script>", "text/html")})

    assert response.status_code == 415
    assert stored == []


def test_empty_file_is_refused(client, stored):
    response = client.post("/recruitment/uploads", files={"file": ("cv.pdf", b"", "application/pdf")})

    assert response.status_code == 400
    assert stored == []


def test_missing_file_is_a_validation_error(client, stored):
    response = client.post("/recruitment/uploads", data={"note": "no file here"})

    assert response.status_code == 422
    assert stored == []


def test_a_body_that_isnt_valid_multipart_is_refused(client, stored):
    response = client.post(
        "/recruitment/uploads",
        content=b"this is not a multipart body",
        headers={"Content-Type": "multipart/form-data; boundary=xyz"},
    )

    assert response.status_code in (400, 422)
    assert stored == []


def test_a_flood_of_form_fields_is_refused(client, stored):
    """Starlette caps the number of parts; a body past the cap must be a 400, not work for the server."""
    boundary = "floodboundary"
    part = f'--{boundary}\r\nContent-Disposition: form-data; name="f"\r\n\r\nx\r\n'
    body = (part * 1500 + f"--{boundary}--\r\n").encode()

    response = client.post(
        "/recruitment/uploads",
        content=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 400
    assert stored == []
