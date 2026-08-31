def _add_expense(client, headers, category, amount, record_date):
    resp = client.post(
        "/api/financial-data/expenses",
        headers=headers,
        json={"category": category, "amount": amount, "frequency": "monthly", "record_date": record_date},
    )
    assert resp.status_code == 200, resp.json()


def test_recommendations_basic_savings_and_expense(auth_client):
    client, headers = auth_client
    for cat in ["income", "expenses"]:
        client.post("/api/consents", headers=headers, json={"data_category": cat})

    client.post(
        "/api/financial-data/income",
        headers=headers,
        json={"source": "Stipend", "amount": 20000, "frequency": "monthly", "record_date": "2026-08-01"},
    )
    _add_expense(client, headers, "Food", 8000, "2026-08-02")

    resp = client.get("/api/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()["data"]
    categories = {r["category"] for r in recs}
    assert "savings" in categories
    assert "expenses" in categories  # Food is 100% of expenses, >= 30% threshold


def test_recommendations_flag_unusual_spending_spike(auth_client):
    """
    Regression/feature test for the scikit-learn based unusual-spending
    detector: four steady months in a category followed by one month that
    spikes well above the historical average should surface a
    'spending_pattern' recommendation naming the actual numbers.
    """
    client, headers = auth_client
    client.post("/api/consents", headers=headers, json={"data_category": "expenses"})

    steady_months = ["2026-03-05", "2026-04-05", "2026-05-05", "2026-06-05"]
    for record_date in steady_months:
        _add_expense(client, headers, "Shopping", 1000, record_date)
    # July: a clear spike relative to the ₹1,000/month history.
    _add_expense(client, headers, "Shopping", 9000, "2026-07-05")

    resp = client.get("/api/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()["data"]

    spending_pattern_recs = [r for r in recs if r["category"] == "spending_pattern"]
    assert len(spending_pattern_recs) == 1
    assert "Shopping" in spending_pattern_recs[0]["message"]
    assert "9,000" in spending_pattern_recs[0]["message"] or "9000" in spending_pattern_recs[0]["message"]
