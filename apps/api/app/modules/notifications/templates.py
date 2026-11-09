"""Standard (fallback) message wording per purpose and language.

These match the templates submitted to Meta. They are used whenever the AI wording is
missing, slow or fails validation (SRS 6.6). Every number is a placeholder.
"""

PLACEHOLDERS: dict[str, list[str]] = {
    "khata_bill": ["{first_name}", "{bill_no}", "{amount}", "{prev_balance}", "{new_balance}", "{pay_link}", "{shop_name}"],
    "payment_receipt": ["{first_name}", "{amount}", "{new_balance}", "{shop_name}"],
    "reminder": ["{first_name}", "{balance}", "{pay_link}", "{shop_name}"],
    "fall_pico_ready": ["{first_name}", "{bill_no}", "{shop_name}"],
    "order_confirmed": ["{first_name}", "{order_no}", "{amount}", "{shop_name}"],
    "return_credit": ["{first_name}", "{amount}", "{new_balance}", "{shop_name}"],
}

STANDARD: dict[str, dict[str, str]] = {
    "khata_bill": {
        "hinglish": "Namaste {first_name} ji, aapka bill {bill_no} ({amount}) ban gaya hai. Pehle ka baaki {prev_balance}, ab kul baaki {new_balance}. Ghar se payment ke liye: {pay_link} - {shop_name}",
        "english": "Hello {first_name}, your bill {bill_no} for {amount} is ready. Previous balance {prev_balance}, total due now {new_balance}. Pay from home: {pay_link} - {shop_name}",
        "hindi": "नमस्ते {first_name} जी, आपका बिल {bill_no} ({amount}) बन गया है। पिछला बाकी {prev_balance}, अब कुल बाकी {new_balance}। घर से भुगतान: {pay_link} - {shop_name}",
    },
    "payment_receipt": {
        "hinglish": "Dhanyavaad {first_name} ji, aapka payment {amount} mil gaya. Ab baaki {new_balance}. - {shop_name}",
        "english": "Thank you {first_name}, we received your payment of {amount}. Balance now {new_balance}. - {shop_name}",
        "hindi": "धन्यवाद {first_name} जी, आपका भुगतान {amount} मिल गया। अब बाकी {new_balance}। - {shop_name}",
    },
    "reminder": {
        "hinglish": "Namaste {first_name} ji, aapka baaki {balance} hai. Suvidha ho to yahan se payment karein: {pay_link} - {shop_name}",
        "english": "Hello {first_name}, a friendly reminder that {balance} is due. You can pay here: {pay_link} - {shop_name}",
        "hindi": "नमस्ते {first_name} जी, आपका बाकी {balance} है। सुविधा हो तो यहाँ भुगतान करें: {pay_link} - {shop_name}",
    },
    "fall_pico_ready": {
        "hinglish": "Namaste {first_name} ji, bill {bill_no} ki saree ka fall-pico ho gaya hai. Aap le ja sakti hain. - {shop_name}",
        "english": "Hello {first_name}, fall-pico for your saree (bill {bill_no}) is ready for pickup. - {shop_name}",
        "hindi": "नमस्ते {first_name} जी, बिल {bill_no} की साड़ी का फॉल-पीको हो गया है। आप ले जा सकती हैं। - {shop_name}",
    },
    "order_confirmed": {
        "hinglish": "Namaste {first_name} ji, aapka order {order_no} ({amount}) confirm ho gaya hai. - {shop_name}",
        "english": "Hello {first_name}, your order {order_no} for {amount} is confirmed. - {shop_name}",
        "hindi": "नमस्ते {first_name} जी, आपका ऑर्डर {order_no} ({amount}) कन्फर्म हो गया है। - {shop_name}",
    },
    "return_credit": {
        "hinglish": "Namaste {first_name} ji, return ke {amount} aapke khate mein jama ho gaye. Ab baaki {new_balance}. - {shop_name}",
        "english": "Hello {first_name}, {amount} for your return has been credited. Balance now {new_balance}. - {shop_name}",
        "hindi": "नमस्ते {first_name} जी, वापसी के {amount} आपके खाते में जमा हो गए। अब बाकी {new_balance}। - {shop_name}",
    },
}


def standard_text(purpose: str, language: str) -> str:
    by_lang = STANDARD[purpose]
    return by_lang.get(language) or by_lang["hinglish"]
