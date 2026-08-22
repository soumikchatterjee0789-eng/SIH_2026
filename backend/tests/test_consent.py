def test_consent_required_before_data_write(auth_client):
    client, headers = auth_client

    resp = client.post(
        "/api/financial-data/income",
        headers=headers,
        json={"source": "Job", "amount": 1000, "frequency": "monthly", "record_date": "2026-08-01"},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "CONSENT_REQUIRED"


def test_consent_grant_then_write_then_revoke(auth_client):
    client, headers = auth_client

    grant = client.post("/api/consents", headers=headers, json={"data_category": "income"})
    assert grant.status_code == 200
    assert grant.json()["data"]["is_active"] is True

    add = client.post(
        "/api/financial-data/income",
        headers=headers,
        json={"source": "Job", "amount": 1000, "frequency": "monthly", "record_date": "2026-08-01"},
    )
    assert add.status_code == 200

    consent_id = grant.json()["data"]["id"]
    revoke = client.delete(f"/api/consents/{consent_id}", headers=headers)
    assert revoke.status_code == 200
    assert revoke.json()["data"]["is_active"] is False

    blocked = client.get("/api/financial-data/income", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error_code"] == "CONSENT_REVOKED"


def test_invalid_consent_category_rejected(auth_client):
    client, headers = auth_client
    resp = client.post("/api/consents", headers=headers, json={"data_category": "religion"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_INPUT"
