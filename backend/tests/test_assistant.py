def test_assistant_insufficient_data(auth_client):
    client, headers = auth_client
    resp = client.post("/api/assistant/chat", headers=headers, json={"message": "Where am I spending the most?"})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["used_insufficient_data_fallback"] is True
    assert "don't have enough" in body["answer"]


def test_assistant_answers_from_real_data(auth_client):
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
        json={"category": "Food", "amount": 9000, "frequency": "monthly", "record_date": "2026-08-02"},
    )

    resp = client.post("/api/assistant/chat", headers=headers, json={"message": "Where am I spending the most?"})
    body = resp.json()["data"]
    assert body["used_insufficient_data_fallback"] is False
    assert "Food" in body["answer"]


def test_assistant_why_score_changed_never_returns_empty_message(auth_client):
    """
    Regression test: a Python operator-precedence bug used to make the
    entire "why did my score change" answer collapse to an empty string
    whenever there were no top scoring factors to report, instead of just
    omitting the "Key factors" clause.
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
    client.get("/api/credit-readiness", headers=headers)

    income = client.get("/api/financial-data/income", headers=headers).json()["data"][0]
    client.put(
        f"/api/financial-data/income/{income['id']}",
        headers=headers,
        json={"amount": 40000, "correction_reason": "correction"},
    )
    client.get("/api/credit-readiness", headers=headers)

    resp = client.post("/api/assistant/chat", headers=headers, json={"message": "Why did my score change?"})
    body = resp.json()["data"]
    assert body["answer"] != ""
    assert "Credit Readiness Score" in body["answer"]
