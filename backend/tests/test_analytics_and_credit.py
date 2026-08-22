def _grant_all(client, headers):
    for cat in ["income", "expenses", "savings", "borrowing", "transactions"]:
        client.post("/api/consents", headers=headers, json={"data_category": cat})


def test_zero_income_never_divides_by_zero(auth_client):
    client, headers = auth_client
    _grant_all(client, headers)

    client.post(
        "/api/financial-data/expenses",
        headers=headers,
        json={"category": "Food", "amount": 500, "frequency": "monthly", "record_date": "2026-08-01"},
    )

    resp = client.get("/api/analytics/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["savings_rate"] is None
    assert data["expense_ratio"] is None
    assert data["total_income"] == 0


def test_financial_summary_math(auth_client):
    client, headers = auth_client
    _grant_all(client, headers)

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

    resp = client.get("/api/analytics/summary", headers=headers)
    data = resp.json()["data"]
    assert data["total_income"] == 20000
    assert data["total_expenses"] == 5000
    assert data["net_cash_flow"] == 15000
    assert data["savings_rate"] == 75.0
    assert data["expense_ratio"] == 25.0


def test_credit_readiness_insufficient_data(auth_client):
    client, headers = auth_client
    _grant_all(client, headers)

    resp = client.get("/api/credit-readiness", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "INSUFFICIENT_DATA"


def test_credit_readiness_score_bounds_and_explanations(auth_client):
    client, headers = auth_client
    _grant_all(client, headers)

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
    client.post(
        "/api/financial-data/savings",
        headers=headers,
        json={"current_savings": 10000, "monthly_savings": 2000, "emergency_savings": 15000, "record_date": "2026-08-05"},
    )

    resp = client.get("/api/credit-readiness", headers=headers)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert 0 <= body["score"] <= 100
    assert body["rating"] in {"Strong", "Moderate", "Developing", "Needs Improvement"}
    assert "not a bureau credit score" in body["disclaimer"]
    assert len(body["factors"]) == 6
    for f in body["factors"]:
        assert f["explanation"]
        assert f["direction"] in {"positive", "negative", "neutral"}


def test_score_changes_after_correction(auth_client):
    client, headers = auth_client
    _grant_all(client, headers)

    # Start just barely above break-even so cash-flow/savings factors sit in
    # a low scoring tier, then correct income enough to cross into the top
    # tier - this is what should move the score (PRD Section 17).
    income = client.post(
        "/api/financial-data/income",
        headers=headers,
        json={"source": "Job", "amount": 4200, "frequency": "monthly", "record_date": "2026-08-01"},
    ).json()["data"]
    client.post(
        "/api/financial-data/expenses",
        headers=headers,
        json={"category": "Food", "amount": 4000, "frequency": "monthly", "record_date": "2026-08-02"},
    )

    first = client.get("/api/credit-readiness", headers=headers).json()["data"]

    client.put(
        f"/api/financial-data/income/{income['id']}",
        headers=headers,
        json={"amount": 50000, "correction_reason": "typo fix"},
    )

    second = client.get("/api/credit-readiness", headers=headers).json()["data"]
    assert second["score"] != first["score"]
