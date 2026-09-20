"""Reproducible arithmetic on the candidate-architecture paper's own reported quantities.

These functions exist because a claim of the form "the paper's numbers are internally
inconsistent" must itself be reproducible code, not prose. Inputs are the paper's own
reported values (EVD-0027); outputs are pure arithmetic. Nothing here estimates a market
quantity.

Reported by the paper (transcribed, EVD-0027):
    0.042          USD per million input tokens (output billed at zero)
    ~240           tokens per state snapshot (inside a stated 400-token budget)
    300 ms         block cadence assumed in the paper's own cost discussion
    ~0.0001 USD    stated marginal cost "near one hundred-thousandth of a dollar per block"
    10-25 USD/month, and 15 USD/month, stated total operating cost
"""

from __future__ import annotations

USD_PER_MILLION_INPUT_TOKENS = 0.042
STATE_TOKENS = 240
TOKEN_BUDGET = 400
BLOCK_CADENCE_MS = 300
STATED_MARGINAL_USD_PER_BLOCK = 0.0001
STATED_MONTHLY_USD = (10.0, 25.0)
STATED_MONTHLY_POINT_USD = 15.0

SECONDS_PER_DAY = 86_400
DAYS_PER_MONTH = 30


def blocks_per_month(cadence_ms=BLOCK_CADENCE_MS, days=DAYS_PER_MONTH):
    """Number of decision blocks in a 24/7 month at a fixed cadence."""
    if cadence_ms <= 0:
        raise ValueError("cadence must be positive")
    return days * SECONDS_PER_DAY * 1000.0 / cadence_ms


def monthly_input_cost_usd(tokens_per_call=STATE_TOKENS, cadence_ms=BLOCK_CADENCE_MS,
                           days=DAYS_PER_MONTH,
                           usd_per_million_tokens=USD_PER_MILLION_INPUT_TOKENS):
    """Monthly input-token cost implied by the paper's own price and cadence."""
    return blocks_per_month(cadence_ms, days) * tokens_per_call * usd_per_million_tokens / 1e6


def monthly_cost_from_stated_marginal(usd_per_block=STATED_MARGINAL_USD_PER_BLOCK,
                                      cadence_ms=BLOCK_CADENCE_MS, days=DAYS_PER_MONTH):
    """Monthly cost implied by the paper's own stated per-block marginal cost."""
    return blocks_per_month(cadence_ms, days) * usd_per_block


def implied_tokens_per_call(usd_per_block=STATED_MARGINAL_USD_PER_BLOCK,
                            usd_per_million_tokens=USD_PER_MILLION_INPUT_TOKENS):
    """Tokens per call required for the stated per-block cost to equal the stated token price."""
    return usd_per_block / (usd_per_million_tokens / 1e6)


def consistency_report():
    """Compare the paper's three cost statements; report ratios, not verdicts about truth."""
    token_path = monthly_input_cost_usd()
    block_path = monthly_cost_from_stated_marginal()
    low, high = STATED_MONTHLY_USD
    return {
        "blocks_per_month": blocks_per_month(),
        "monthly_cost_from_token_price_and_240_token_state_usd": token_path,
        "monthly_cost_from_stated_marginal_cost_usd": block_path,
        "stated_monthly_usd_range": [low, high],
        "stated_monthly_point_usd": STATED_MONTHLY_POINT_USD,
        "ratio_token_path_to_stated_point": token_path / STATED_MONTHLY_POINT_USD,
        "ratio_block_path_to_stated_point": block_path / STATED_MONTHLY_POINT_USD,
        "implied_tokens_per_call_for_stated_marginal": implied_tokens_per_call(),
        "stated_state_tokens": STATE_TOKENS,
        "consistent": bool(
            low <= token_path <= high and low <= block_path <= high),
    }
