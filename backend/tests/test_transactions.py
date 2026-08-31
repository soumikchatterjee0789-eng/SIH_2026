import io


def test_csv_preview_then_confirm(auth_client):
    client, headers = auth_client
    client.post("/api/consents", headers=headers, json={"data_category": "transactions"})

    csv_content = (
        "date,description,amount,type,category\n"
        "2026-08-01,Salary,18000,income,Salary\n"
        "2026-08-02,Hostel,6000,expense,Housing\n"
        "2026-08-03,BadAmount,notanumber,expense,Food\n"
    )
    files = {"file": ("sample.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    preview = client.post("/api/transactions/upload", headers=headers, files=files, data={"confirm": "false"})
    assert preview.status_code == 200
    body = preview.json()["data"]
    assert body["total_rows"] == 3
    assert body["valid_rows"] == 2
    assert body["invalid_rows"] == 1
    batch_token = body["batch_token"]

    # nothing stored yet
    listed = client.get("/api/transactions", headers=headers)
    assert listed.json()["data"] == []

    files2 = {"file": ("sample.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    confirm = client.post(
        "/api/transactions/upload",
        headers=headers,
        files=files2,
        data={"confirm": "true", "batch_token": batch_token},
    )
    assert confirm.status_code == 200
    assert confirm.json()["data"]["inserted_count"] == 2

    listed2 = client.get("/api/transactions", headers=headers)
    assert len(listed2.json()["data"]) == 2


def test_csv_missing_required_column_rejected(auth_client):
    client, headers = auth_client
    client.post("/api/consents", headers=headers, json={"data_category": "transactions"})

    csv_content = "description,amount\nSalary,18000\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    resp = client.post("/api/transactions/upload", headers=headers, files=files, data={"confirm": "false"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_TRANSACTION"
