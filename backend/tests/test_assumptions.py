from app.services.assumptions import infer_target_customer


def test_infer_target_customer_from_poi_mix():
    target = infer_target_customer(
        [
            {"radius": 1000, "categories": {"office": 25, "residential": 12, "transport": 8, "retail": 10}},
        ],
        "咖啡店",
    )

    assert "办公白领" in target
    assert "通勤人群" in target
