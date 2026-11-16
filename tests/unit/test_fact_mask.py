"""事实层的单元测试：不连数据库、不调模型。"""
from datetime import date

from quarry.facts.attach import FactMasker, verified_date
from quarry.facts.contract import check_item, normalize_value

PARENT = "兵马俑博物馆门票 120 元，旺季开放时间 8:30 至 18:00。回民街人均 60 元。"


def mention(quote, attribute, written, official=None, verified=None):
    start = PARENT.index(quote)
    return {"chunk_id": "P1", "span_start": start, "span_end": start + len(quote),
            "entity_name": "兵马俑博物馆", "attribute": attribute, "qualifier": "旺季",
            "written_value": written,
            "official_name": "秦始皇帝陵博物院" if official else None,
            "official_value": official, "verified_at": verified, "source_url": None}


def test_mask_then_finalize():
    rows = [mention("120 元", "ticket_price", "120",
                    official="150", verified=date(2026, 9, 1)),
            mention("8:30 至 18:00", "open_hours", "08:30-18:00")]
    masker = FactMasker(rows, ttl_days=90, today=date(2026, 9, 17))
    [ctx], [facts] = masker.finalize([masker.mask("P1", PARENT)])

    assert "120" not in ctx and "8:30" not in ctx
    assert "〔F1 门票价格〕" in ctx and "〔F2 开放时间〕" in ctx
    assert "60 元" in ctx                                     # 没抽取的数值保持原样
    assert [f.value for f in facts] == ["150", "08:30-18:00"]
    assert [f.status for f in facts] == ["verified", "unverified"]
    assert facts[0].written_values == ["120"]
    assert verified_date(facts) is None                       # 有未核实的数值，卡片不显示日期


def test_mask_child_window_with_offset():
    masker = FactMasker([mention("8:30 至 18:00", "open_hours", "08:30-18:00")],
                        ttl_days=90)
    offset = PARENT.index("旺季")
    child = PARENT[offset:offset + 20]
    assert "〔F1 开放时间〕" in masker.mask("P1", child, offset=offset)
    assert masker.mask("P1", PARENT[:10]) == PARENT[:10]      # 提及不在这段文字里，原样返回


def test_expired_status_and_card_date():
    rows = [mention("120 元", "ticket_price", "120",
                    official="150", verified=date(2026, 1, 1))]
    masker = FactMasker(rows, ttl_days=90, today=date(2026, 9, 17))
    _, [facts] = masker.finalize([masker.mask("P1", PARENT)])
    assert facts[0].status == "expired"
    assert verified_date(facts) == date(2026, 1, 1)


def test_contract_normalizes_and_rejects():
    assert normalize_value("open_hours", "8:30至18:00") == "08:30-18:00"
    assert normalize_value("open_hours", "18:00-8:30") is None
    assert normalize_value("ticket_price", "免费") == "0"
    assert normalize_value("ticket_price", "120元") == "120"
    too_long = {"entity": "某景点", "attribute": "ticket_price", "value": "120",
                "quote": "这一整句话都被模型当成了原文片段，太长了，"
                         "遮蔽时会误伤一大段，门票 120 元"}
    assert check_item(too_long) == (None, "原文片段不合规")