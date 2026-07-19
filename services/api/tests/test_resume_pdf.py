"""PDF resume upload -> text extraction -> stored on the profile."""
import base64

# Minimal single-page PDF (generated for this test) whose text stream reads
# "Kafka migration lead at AcmeCorp, 50k msg/s".
FIXTURE_PDF = base64.b64decode(
    "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoK"
    "PDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUg"
    "L1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291"
    "cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA3NCA+"
    "PgpzdHJlYW0KQlQgL0YxIDEyIFRmIDcyIDcyMCBUZCAoS2Fma2EgbWlncmF0aW9uIGxlYWQgYXQgQWNtZUNvcnAs"
    "IDUwayBtc2cvcykgVGogRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8IC9UeXBlIC9Gb250IC9TdWJ0eXBl"
    "IC9UeXBlMSAvQmFzZUZvbnQgL0hlbHZldGljYSA+PgplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBm"
    "IAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAw"
    "MDAwMjQxIDAwMDAwIG4gCjAwMDAwMDAzNjUgMDAwMDAgbiAKdHJhaWxlcgo8PCAvU2l6ZSA2IC9Sb290IDEgMCBS"
    "ID4+CnN0YXJ0eHJlZgo0MzUKJSVFT0Y="
)


def test_pdf_upload_extracts_and_stores_resume(client, auth_headers):
    resp = client.post("/api/profile/resume-upload", content=FIXTURE_PDF,
                       headers={**auth_headers, "Content-Type": "application/pdf"})
    assert resp.status_code == 200, resp.text
    text = resp.json()["profile"]["resume_text"]
    assert "Kafka migration lead at AcmeCorp" in text

    # Stored: a fresh GET returns it too.
    prof = client.get("/api/profile", headers=auth_headers).json()
    assert "AcmeCorp" in prof["profile"]["resume_text"]


def test_pdf_upload_rejects_non_pdf(client, auth_headers):
    resp = client.post("/api/profile/resume-upload", content=b"plain text bytes",
                       headers=auth_headers)
    assert resp.status_code == 400
