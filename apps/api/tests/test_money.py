from app.core.money import format_inr, rupees_to_paise


def test_rupees_to_paise():
    assert rupees_to_paise("1499.50") == 149950
    assert rupees_to_paise(1000) == 100000


def test_format_inr_indian_grouping():
    assert format_inr(149900) == "₹1,499.00"
    assert format_inr(123456700) == "₹12,34,567.00"
    assert format_inr(-5000) == "-₹50.00"
