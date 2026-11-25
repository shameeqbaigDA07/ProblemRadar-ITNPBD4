"""Tests for quote verification against the retrieved source text."""

from conftest import ARTICLE_A
from scoring import verify_quote


def test_exact_quote_is_verified():
    assert verify_quote("recruiting qualified veterinary nurses has become the single biggest", ARTICLE_A)


def test_case_spacing_and_punctuation_are_ignored():
    quote = "  RECRUITING qualified veterinary   nurses, has become the single biggest  "
    assert verify_quote(quote, ARTICLE_A)


def test_curly_quotes_and_dashes_are_treated_like_plain_ones():
    text = "Owners said “it’s impossible to hire” — every single month this year."
    assert verify_quote('Owners said "it\'s impossible to hire" - every single month', text)


def test_changed_word_is_not_verified():
    assert not verify_quote("recruiting qualified veterinary doctors has become the single biggest", ARTICLE_A)


def test_invented_quote_is_not_verified():
    assert not verify_quote("clinics are desperate for an AI receptionist to answer calls", ARTICLE_A)


def test_joined_fragments_are_not_verified():
    # Two real fragments stitched together do not appear in the source as one quote.
    assert not verify_quote("vacancies left open for six months rural practices", ARTICLE_A)


def test_very_short_quote_is_not_verified():
    assert not verify_quote("vet clinics report", ARTICLE_A)


def test_empty_inputs_are_not_verified():
    assert not verify_quote("", ARTICLE_A)
    assert not verify_quote("recruiting qualified veterinary nurses has become", "")


def test_partial_word_match_is_not_verified():
    # "nurse" must not match inside "nurses" at the end of a quote.
    assert not verify_quote("recruiting qualified veterinary nurse has become the", ARTICLE_A)



# ---- regression: first live run (17 Nov 2026) ------------------------------
# Gemini copied a real sentence but the prompt excerpt had been cut mid-word,
# so the quote ended in "tighter regul". The checker wrongly rejected it.

LIVE_SOURCE = ("Agencies that build these systems early will protect profitability, strengthen "
               "CQC outcomes, and grow despite rising wage pressure, tighter regulation and "
               "workforce shortages.")


def test_quote_with_cut_off_last_word_is_verified():
    quote = ("Agencies that build these systems early will protect profitability, strengthen CQC "
             "outcomes, and grow despite rising wage pressure, tighter regul")
    assert verify_quote(quote, LIVE_SOURCE)


def test_cut_off_last_word_must_still_match_its_start():
    assert not verify_quote("grow despite rising wage pressure, tighter rules", LIVE_SOURCE)


def test_cut_off_word_in_the_middle_is_not_allowed():
    assert not verify_quote("grow despite rising wage pres, tighter regulation", LIVE_SOURCE)


def test_very_short_cut_off_word_is_not_allowed():
    assert not verify_quote("grow despite rising wage pressure, ti", LIVE_SOURCE)
