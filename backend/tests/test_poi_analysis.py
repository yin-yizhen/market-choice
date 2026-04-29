from app.services.poi import classify_poi, summarize_ring


def test_classify_poi_detects_major_categories_and_competitors():
    coffee_shop = {
        "name": "Manner Coffee",
        "type": "餐饮服务;咖啡厅;咖啡厅",
        "typecode": "050500",
    }
    parking = {
        "name": "万象城地下停车场",
        "type": "交通设施服务;停车场;公共停车场",
        "typecode": "150900",
    }

    assert classify_poi(coffee_shop, "咖啡店") == {
        "category": "food",
        "is_competitor": True,
        "is_complementary": False,
    }
    assert classify_poi(parking, "咖啡店") == {
        "category": "parking",
        "is_competitor": False,
        "is_complementary": True,
    }


def test_summarize_ring_counts_categories_competitors_and_complements():
    pois = [
        {"name": "瑞幸咖啡", "type": "餐饮服务;咖啡厅", "typecode": "050500"},
        {"name": "写字楼A座", "type": "商务住宅;楼宇;商务写字楼", "typecode": "120200"},
        {"name": "地铁站", "type": "交通设施服务;地铁站", "typecode": "150500"},
        {"name": "停车场", "type": "交通设施服务;停车场", "typecode": "150900"},
    ]

    summary = summarize_ring(500, pois, "咖啡店")

    assert summary["radius"] == 500
    assert summary["total"] == 4
    assert summary["categories"]["food"] == 1
    assert summary["categories"]["office"] == 1
    assert summary["categories"]["transport"] == 1
    assert summary["categories"]["parking"] == 1
    assert summary["competitor_count"] == 1
    assert summary["complementary_count"] == 3
