from app.modules.notifications.validator import validate_and_fill

REQ = ["{amount}", "{new_balance}"]
VALUES = {"amount": "₹1,499", "new_balance": "₹3,499"}


def test_good_text_is_filled():
    text = "Namaste, bill {amount} ban gaya. Ab kul baaki {new_balance}. Dhanyavaad!"
    assert validate_and_fill(text, REQ, VALUES) == "Namaste, bill ₹1,499 ban gaya. Ab kul baaki ₹3,499. Dhanyavaad!"


def test_model_written_number_is_rejected():
    assert validate_and_fill("Bill {amount}, baaki {new_balance}, pay by 5 Oct", REQ, VALUES) is None


def test_missing_or_unknown_placeholder_is_rejected():
    assert validate_and_fill("Bill {amount} ban gaya", REQ, VALUES) is None
    assert validate_and_fill("Bill {amount} {new_balance} {extra}", REQ, VALUES) is None
