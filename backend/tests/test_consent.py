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


def test_revoking_consent_immediately_excludes_data_from_analytics(auth_client):
    """
    PRD principle: "Revoking consent immediately blocks further use."
    Revoking a category's consent must stop that data from being counted
    in analytics right away - the records stay in the database (for
    potential re-consent later), but they must not affect any numbers
    shown to the user until consent is granted again.
    """
    client, headers = auth_client

    for cat in ["income", "expenses"]:
        client.post("/api/consents", headers=headers, json={"data_category": cat})

    client.post(
        "/api/financial-data/income",
        headers=headers,
        json={"source": "Job", "amount": 20000, "frequency": "monthly", "record_date": "2026-08-01"},
    )
    client.post(
        "/api/financial-data/expenses",
        headers=headers,
        json={"category": "Food", "amount": 5000, "frequency": "monthly", "record_date": "2026-08-02"},
    )

    before = client.get("/api/analytics/summary", headers=headers).json()["data"]
    assert before["total_income"] == 20000
    assert before["total_expenses"] == 5000

    consents = client.get("/api/consents", headers=headers).json()["data"]
    income_consent_id = next(c["id"] for c in consents if c["data_category"] == "income" and c["is_active"])
    client.delete(f"/api/consents/{income_consent_id}", headers=headers)

    after = client.get("/api/analytics/summary", headers=headers).json()["data"]
    assert after["total_income"] == 0
    assert after["total_expenses"] == 5000

    breakdown = client.get("/api/analytics/expenses", headers=headers).json()["data"]
    assert breakdown["total_expenses"] == 5000
