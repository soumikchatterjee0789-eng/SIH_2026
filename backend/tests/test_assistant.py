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
