from tally_logic import build_reaction_key, format_result_channel_name, reaction_sign


def test_reaction_sign_green_check_is_win():
    assert reaction_sign("✅") == 1
    assert reaction_sign("green_check") == 1


def test_reaction_sign_red_x_is_loss():
    assert reaction_sign("❌") == -1
    assert reaction_sign("red_x") == -1


def test_result_channel_name_formats_day_week_year():
    name = format_result_channel_name(3, 9, 42)
    assert name == "D: +3 | W: +9 | Y: +42"


def test_build_reaction_key_is_stable_for_same_event():
    key1 = build_reaction_key(123, 456, "✅")
    key2 = build_reaction_key("123", "456", "✅")
    assert key1 == key2 == "123:456:✅"
