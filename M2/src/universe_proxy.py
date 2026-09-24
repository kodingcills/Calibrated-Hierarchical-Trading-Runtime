"""Single-day liquidity proxy for the frozen universe rule (M2-0.6).

The frozen rule ``NASDAQ-LARGETICK-QIMB-UNIV-v1`` selects, from Nasdaq-listed common
stock that passes a price floor, the **top decile of trailing 60-trading-day median
daily dollar volume**, and then requires the large-tick screen (median quoted spread
equal to one tick AND at least THETA of valid book observations at one tick) over the
same lookback.

A single free sample day cannot supply that lookback, so this module does not claim
membership. It computes the rule's own *liquidity* input on one day and labels every
row as a proxy:

* dollar volume is accumulated from the venue's own trade tape (order executions at
  the resting order's price, order executions with a price, and non-cross trades);
* the price floor uses the day's trade prices (the rule's variable is a trade-price
  statistic);
* the decile is taken with the rule's own primitive, ``universe.top_decile_by_dollar_volume``,
  so the ranking *convention* is the frozen one and only the observation window is
  substituted.

What this module deliberately does not do: it does not evaluate coverage, listing
history, corporate actions or halt frequency, and it does not claim eligibility.
Those fields are left null in its output, exactly as ``universe.blocked_membership_rows``
leaves the point-in-time reference null. The output exists to answer one question -
whether the economics measured on the M2-0 compute scope are an artifact of that
scope - and it may never be renamed a membership artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Iterable

import numpy as np

from . import config as config_module
from . import ingest
from . import universe

PROXY_STATUS = "SINGLE_DAY_LIQUIDITY_PROXY_NOT_UNIVERSE_MEMBERSHIP"
PROXY_REASON_ELIGIBLE = "PROXY_LIQUIDITY_DECILE"
PROXY_REASON_NOT_DECILE = "LIQUIDITY_OUTSIDE_TOP_DECILE"
PROXY_REASON_PRICE = "PRICE_BELOW_1_USD"
PROXY_REASON_NO_TRADES = "NO_TRADES_ON_SAMPLE_DAY"
PROXY_REASON_SECURITY = "SECURITY_TYPE_EXCLUDED"
LARGE_TICK_PROXY_STATUS = "LARGE_TICK_PROXY_SINGLE_DAY_NOT_MEMBERSHIP"
PROXY_MINIMUM_SPREAD_OBSERVATIONS = 1000

# Message type bytes used by the trade tape. Book-modifying types are handled only to
# keep the live-order price map bounded; trade types produce the volume.
TYPE_ADD = 0x41
TYPE_ADD_MPID = 0x46
TYPE_EXECUTED = 0x45
TYPE_EXECUTED_WITH_PRICE = 0x43
TYPE_CANCEL = 0x58
TYPE_DELETE = 0x44
TYPE_REPLACE = 0x55
TYPE_TRADE = 0x50
TYPE_CROSS = 0x51

# Payload offsets, from the provider specification through the same constants the
# replay engine uses (see M2/src/book.py, which decodes the identical layout).
R_ORDER_REF = 11
R_SHARES_ADD = 20
R_PRICE_ADD = 32
R_EXECUTED = 19
R_CANCEL = 19
R_NEW_REF = 19
R_SHARES_REPLACE = 27
R_PRICE_REPLACE = 31
R_SHARES_TRADE = 20
R_PRICE_TRADE = 32
R_PRICE_EXECUTED_WITH_PRICE = 32

REMAINING_MASK = 0xFFFFFFFF
PRICE_SHIFT = 32

# A day of whole-venue order flow holds a few million live orders at any instant; the
# packed (price, remaining) value keeps that map an order of magnitude smaller than a
# tuple-per-order representation, which matters because this pass is single-threaded.
PROGRESS_EVERY = 20_000_000


class LiquidityScan:
    """Accumulators for one sequential pass over the trade tape."""

    def __init__(self) -> None:
        self.dollar_volume: dict[int, int] = {}
        self.shares: dict[int, int] = {}
        self.trades: dict[int, int] = {}
        # Crossing sessions are counted, not priced: the liquidity measure is a
        # continuous-session quantity by definition, and this repository does not carry
        # a verified field layout for the Cross Trade message, so nothing is inferred
        # from it.
        self.cross_messages: dict[int, int] = {}
        self.price_trades: dict[int, dict[int, int]] = {}
        self.messages = 0
        self.frames_verified = 0
        self.orphan_executes = 0
        self.orphan_cancels = 0
        self.duplicate_add_refs = 0
        self.max_live_orders = 0

    def record_trade(self, locate: int, price_raw: int, shares: int, histogram: bool) -> None:
        self.dollar_volume[locate] = self.dollar_volume.get(locate, 0) + price_raw * shares
        self.shares[locate] = self.shares.get(locate, 0) + shares
        self.trades[locate] = self.trades.get(locate, 0) + 1
        if histogram:
            bucket = self.price_trades.setdefault(locate, {})
            bucket[price_raw] = bucket.get(price_raw, 0) + 1

    def median_trade_price_raw(self, locate: int) -> float | None:
        bucket = self.price_trades.get(locate)
        if not bucket:
            return None
        total = sum(bucket.values())
        target = (total - 1) / 2.0
        running = 0
        for price in sorted(bucket):
            running += bucket[price]
            if running > target:
                return float(price)
        return float(max(bucket))


def scan_liquidity(raw_path: str, tracked: set[int] | None = None, progress: bool = False) -> LiquidityScan:
    """One sequential pass: dollar volume per locate from the venue trade tape.

    Only locates in ``tracked`` (the eligible security set) have their order state
    maintained; every other locate is decoded for framing integrity and counted in
    ``scan.messages`` only.
    """
    scan = LiquidityScan()
    orders: dict[int, int] = {}
    header = ingest.HEADER
    u64 = ingest.U64
    u32 = ingest.U32
    message_lengths = ingest.MSG_LENGTH
    with ingest.open_source(raw_path) as handle:
        buffer = bytearray()
        position = 0
        while True:
            block = handle.read(ingest.CHUNK)
            if not block:
                break
            buffer += block
            view = memoryview(buffer)
            limit = len(view)
            while position + 1 < limit:
                declared = (view[position] << 8) | view[position + 1]
                if position + ingest.FRAME_PREFIX + declared > limit:
                    break
                base = position + ingest.FRAME_PREFIX
                message_type = view[base]
                expected = message_lengths.get(message_type)
                if expected is None:
                    raise ingest.FeedFormatError(
                        f"unknown message type byte 0x{message_type:02x} at stream offset {base}"
                    )
                if declared != expected:
                    raise ingest.FeedFormatError(
                        f"framing mismatch: type 0x{message_type:02x} declares {declared}, documented {expected}"
                    )
                locate, _tracking, _ts_hi, _ts_lo = header.unpack_from(buffer, base + 1)
                scan.messages += 1
                scan.frames_verified += 1
                if progress and scan.messages % PROGRESS_EVERY == 0:
                    print(f"  scanned {scan.messages:,} messages, {len(orders):,} live orders", flush=True)
                in_scope = tracked is None or locate in tracked
                if in_scope:
                    if message_type == TYPE_ADD or message_type == TYPE_ADD_MPID:
                        ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        shares = u32.unpack_from(buffer, base + R_SHARES_ADD)[0]
                        price = u32.unpack_from(buffer, base + R_PRICE_ADD)[0]
                        if ref in orders:
                            scan.duplicate_add_refs += 1
                        orders[ref] = (price << PRICE_SHIFT) | shares
                    elif message_type == TYPE_REPLACE:
                        original = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        replacement = u64.unpack_from(buffer, base + R_NEW_REF)[0]
                        shares = u32.unpack_from(buffer, base + R_SHARES_REPLACE)[0]
                        price = u32.unpack_from(buffer, base + R_PRICE_REPLACE)[0]
                        orders.pop(original, None)
                        orders[replacement] = (price << PRICE_SHIFT) | shares
                    elif message_type == TYPE_DELETE:
                        ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        orders.pop(ref, None)
                    elif message_type == TYPE_CANCEL:
                        ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        cancelled = u32.unpack_from(buffer, base + R_CANCEL)[0]
                        packed = orders.get(ref)
                        if packed is None:
                            scan.orphan_cancels += 1
                        else:
                            remaining = (packed & REMAINING_MASK) - cancelled
                            if remaining <= 0:
                                del orders[ref]
                            else:
                                orders[ref] = (packed & ~REMAINING_MASK) | remaining
                    elif message_type == TYPE_EXECUTED:
                        ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        executed = u32.unpack_from(buffer, base + R_EXECUTED)[0]
                        packed = orders.get(ref)
                        if packed is None:
                            scan.orphan_executes += 1
                        else:
                            price = packed >> PRICE_SHIFT
                            scan.record_trade(locate, price, executed, True)
                            remaining = (packed & REMAINING_MASK) - executed
                            if remaining <= 0:
                                del orders[ref]
                            else:
                                orders[ref] = (packed & ~REMAINING_MASK) | remaining
                    elif message_type == TYPE_EXECUTED_WITH_PRICE:
                        ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                        executed = u32.unpack_from(buffer, base + R_EXECUTED)[0]
                        price = u32.unpack_from(buffer, base + R_PRICE_EXECUTED_WITH_PRICE)[0]
                        packed = orders.get(ref)
                        if packed is None:
                            scan.orphan_executes += 1
                        else:
                            remaining = (packed & REMAINING_MASK) - executed
                            if remaining <= 0:
                                del orders[ref]
                            else:
                                orders[ref] = (packed & ~REMAINING_MASK) | remaining
                        scan.record_trade(locate, price, executed, True)
                    elif message_type == TYPE_TRADE:
                        shares = u32.unpack_from(buffer, base + R_SHARES_TRADE)[0]
                        price = u32.unpack_from(buffer, base + R_PRICE_TRADE)[0]
                        scan.record_trade(locate, price, shares, True)
                    elif message_type == TYPE_CROSS:
                        scan.cross_messages[locate] = scan.cross_messages.get(locate, 0) + 1
                scan.max_live_orders = max(scan.max_live_orders, len(orders))
                position += ingest.FRAME_PREFIX + declared
            buffer = buffer[position:]
            position = 0
        ingest.check_no_trailing_bytes(buffer)
    return scan


def security_type_eligible(entry: dict) -> bool:
    """The frozen rule's security-type screen, as the directory expresses it."""
    if entry["market_category"] not in ingest.NASDAQ_LISTED_CATEGORIES:
        return False
    if entry["issue_classification"] != "C":
        return False
    if entry["etp_flag"] == "Y":
        return False
    return entry["authenticity"] == "P"


def proxy_membership(
    configuration: dict,
    scan: LiquidityScan,
    directory: dict[int, dict],
) -> list[dict]:
    """Liquidity proxy rows in the frozen rule's own order of reasoning."""
    scale = float(configuration["price_scale"])
    price_floor_raw = float(configuration["price_floor_usd"]) * scale
    decile_fraction = float(configuration["universe"].get("liquidity_decile_fraction", 0.10))

    rows: list[dict] = []
    for locate, entry in sorted(directory.items(), key=lambda item: item[1]["symbol"]):
        if not security_type_eligible(entry):
            continue
        median_price_raw = scan.median_trade_price_raw(locate)
        price_ok = median_price_raw is not None and median_price_raw >= price_floor_raw
        rows.append(
            {
                "locate": locate,
                "symbol": entry["symbol"],
                "market_category": entry["market_category"],
                "issue_classification": entry["issue_classification"],
                "dollar_volume_usd": scan.dollar_volume.get(locate, 0) / scale,
                "shares_traded": scan.shares.get(locate, 0),
                "trade_count": scan.trades.get(locate, 0),
                "cross_messages": scan.cross_messages.get(locate, 0),
                "median_trade_price_usd": None if median_price_raw is None else median_price_raw / scale,
                "price_ok": price_ok,
                "median_dollar_volume": scan.dollar_volume.get(locate, 0) / scale,
            }
        )

    observations = [
        universe.SymbolObservation(
            symbol=row["symbol"],
            price_ok=bool(row["price_ok"]),
            median_dollar_volume=float(row["median_dollar_volume"]),
        )
        for row in rows
    ]
    decile = {
        observation.symbol
        for observation in universe.top_decile_by_dollar_volume(observations, decile_fraction)
    }
    ranked = sorted(rows, key=lambda row: (-row["dollar_volume_usd"], row["symbol"]))
    rank_of: dict[str, int] = {}
    for rank, row in enumerate(ranked):
        rank_of[row["symbol"]] = rank
    liquidity_ranked = [row for row in ranked if row["price_ok"]]
    liquidity_rank_of = {row["symbol"]: rank for rank, row in enumerate(liquidity_ranked)}

    for row in rows:
        row["liquidity_rank_all_eligible"] = rank_of[row["symbol"]]
        if not row["price_ok"]:
            row["reason_code"] = (
                PROXY_REASON_NO_TRADES if row["median_trade_price_usd"] is None else PROXY_REASON_PRICE
            )
            row["liquidity_rank"] = None
            row["in_liquidity_decile"] = False
        else:
            row["liquidity_rank"] = liquidity_rank_of[row["symbol"]]
            row["in_liquidity_decile"] = row["symbol"] in decile
            row["reason_code"] = (
                PROXY_REASON_ELIGIBLE if row["in_liquidity_decile"] else PROXY_REASON_NOT_DECILE
            )
        row["proxy_status"] = PROXY_STATUS
        row["reporting_only"] = True
    return rows


def scope_locates(rows: Iterable[dict], size: int) -> list[dict]:
    """The replay scope: the ``size`` largest dollar-volume names inside the decile."""
    inside = [row for row in rows if row.get("in_liquidity_decile")]
    inside.sort(key=lambda row: (row["liquidity_rank"], row["symbol"]))
    return inside[:size]


def classify_large_tick_proxy(
    configuration: dict,
    derived: str,
    symbol_map: dict[int, str],
    minimum_observations: int = PROXY_MINIMUM_SPREAD_OBSERVATIONS,
) -> list[dict]:
    """Apply the frozen rule's large-tick sentences to the day's replay observations.

    Median quoted spread and the fraction of valid observations at one tick are computed
    per symbol over the 1 s decision grid of the replayed scope. This is a one-day proxy
    of the rule's 60-trading-day lookback: the sentences are the rule's own (median
    exactly one tick AND fraction >= THETA), the window is not.
    """
    import pyarrow.parquet as pq

    theta = float(configuration["universe"]["theta_fraction_at_one_tick"])
    tick_raw = int(configuration["tick_raw"])
    table = pq.read_table(
        os.path.join(derived, "decisions.parquet"), columns=["locate", "spread_raw", "mid2_raw"]
    )
    locate = table["locate"].to_numpy(zero_copy_only=False)
    spread = table["spread_raw"].to_numpy(zero_copy_only=False).astype("float64")
    mid2 = table["mid2_raw"].to_numpy(zero_copy_only=False).astype("float64")
    valid = (mid2 > 0) & (spread > 0)
    rows: list[dict] = []
    for code in sorted(set(locate.tolist())):
        mask = valid & (locate == code)
        observations = int(mask.sum())
        spreads = spread[mask]
        if observations:
            median_spread = float(np.median(spreads))
            fraction = float(np.mean(spreads == tick_raw))
        else:
            median_spread = None
            fraction = None
        median_is_tick = median_spread == float(tick_raw)
        fraction_ok = fraction is not None and fraction >= theta
        enough = observations >= minimum_observations
        rows.append(
            {
                "locate": int(code),
                "symbol": symbol_map.get(int(code), ""),
                "valid_observations": observations,
                "median_spread_ticks": None if median_spread is None else median_spread / tick_raw,
                "fraction_at_one_tick": fraction,
                "median_spread_equals_one_tick": median_is_tick,
                "fraction_threshold_met": fraction_ok,
                "minimum_observations_met": enough,
                "large_tick_proxy": bool(enough and median_is_tick and fraction_ok),
                "proxy_status": LARGE_TICK_PROXY_STATUS,
                "reporting_only": True,
            }
        )
    rows.sort(key=lambda row: (-(row["fraction_at_one_tick"] or 0.0), row["symbol"]))
    return rows


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", newline="") as handle:
            handle.write("empty:no_rows\n")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M2-0.6 stage 1: single-day liquidity proxy and replay scope manifest."
    )
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0_6_univproxy.yaml")
    parser.add_argument(
        "--stage",
        choices=["liquidity", "classify"],
        default="liquidity",
        help="liquidity: scan the tape and write the replay scope; classify: apply the large-tick proxy screen to a replay",
    )
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    if arguments.stage == "classify":
        return classify_main(configuration, arguments.config)
    paths = configuration["paths"]
    raw_path = config_module.repo_path(os.path.join(paths["raw_dir"], configuration["dataset"]["raw_files"][0]))
    directory = ingest.read_symbol_directory(raw_path)
    tracked = {locate for locate, entry in directory.items() if security_type_eligible(entry)}
    print(f"security-type eligible locates: {len(tracked):,} of {len(directory):,}", flush=True)
    scan = scan_liquidity(raw_path, tracked, progress=True)
    print(f"scan complete: {scan.messages:,} messages, max live orders {scan.max_live_orders:,}", flush=True)

    rows = proxy_membership(configuration, scan, directory)
    decile_rows = [row for row in rows if row["in_liquidity_decile"]]
    size = int(configuration["dev_scope"]["proxy_scope_size"])
    selected = scope_locates(rows, size)

    with open(config_module.repo_path(os.path.join(paths["manifest_dir"], "proxy_scope_manifest.json")), "w") as handle:
        json.dump(
            {
                "status": PROXY_STATUS,
                "basis": "SINGLE_SAMPLE_DAY_LIQUIDITY_PROXY",
                "coverage_date": configuration["dataset"]["coverage_date"],
                "universe_rule_id": configuration["universe"]["rule_version"],
                "raw_sha256": ingest.sha256_file(raw_path),
                "code_sha256": config_module.sha256_file("M2/src/universe_proxy.py"),
                "selection_variable": "same-day dollar volume from the venue trade tape (E at the resting "
                                      "order price, C at the execution price, P non-cross trades); crosses excluded",
                "decile_fraction": float(configuration["universe"].get("liquidity_decile_fraction", 0.10)),
                "security_type_eligible": len(rows),
                "decile_members": len(decile_rows),
                "scope_size": size,
                "scope_status": "REPLAY_SCOPE_NOT_UNIVERSE_MEMBERSHIP",
                "scope_locates": [
                    {"locate": row["locate"], "symbol": row["symbol"], "liquidity_rank": row["liquidity_rank"],
                     "dollar_volume_usd": row["dollar_volume_usd"], "median_trade_price_usd": row["median_trade_price_usd"]}
                    for row in selected
                ],
                "decile_locates": [
                    {"locate": row["locate"], "symbol": row["symbol"], "liquidity_rank": row["liquidity_rank"],
                     "dollar_volume_usd": row["dollar_volume_usd"], "median_trade_price_usd": row["median_trade_price_usd"]}
                    for row in decile_rows
                ],
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")

    data_quality = config_module.ensure_dirs(configuration, "data_quality")
    write_csv(os.path.join(data_quality, "proxy_liquidity_scan.csv"), rows)
    config_module.write_json(
        os.path.join(data_quality, "proxy_liquidity_summary.json"),
        {
            "status": PROXY_STATUS,
            "messages_scanned": scan.messages,
            "frames_verified": scan.frames_verified,
            "max_live_orders": scan.max_live_orders,
            "orphan_executes": scan.orphan_executes,
            "orphan_cancels": scan.orphan_cancels,
            "duplicate_add_refs": scan.duplicate_add_refs,
            "security_type_eligible": len(rows),
            "price_ok": sum(1 for row in rows if row["price_ok"]),
            "decile_members": len(decile_rows),
            "scope_size": size,
            "scope_locates": [row["symbol"] for row in selected],
            "config_sha256": config_module.sha256_file(arguments.config),
        },
    )
    print(f"decile members {len(decile_rows)}, replay scope {len(selected)} symbols", flush=True)
    return 0


def classify_main(configuration: dict, config_path: str) -> int:
    """Stage 3: the large-tick proxy subset, from the replay's own observations."""
    from . import calculate

    derived = config_module.repo_path(config_module.derived_dir(configuration))
    symbol_map = calculate.load_symbol_map(derived)
    rows = classify_large_tick_proxy(configuration, derived, symbol_map)
    data_quality = config_module.ensure_dirs(configuration, "data_quality")
    write_csv(os.path.join(data_quality, "large_tick_proxy_membership.csv"), rows)
    subset = [row for row in rows if row["large_tick_proxy"]]
    write_csv(
        os.path.join(data_quality, "large_tick_proxy_subset.csv"),
        [{"locate": row["locate"], "symbol": row["symbol"]} for row in subset],
    )
    config_module.write_json(
        os.path.join(data_quality, "large_tick_proxy_summary.json"),
        {
            "proxy_status": LARGE_TICK_PROXY_STATUS,
            "scope_symbols": len(rows),
            "large_tick_proxy_symbols": len(subset),
            "excluded_for_observation_count": sum(1 for row in rows if not row["minimum_observations_met"]),
            "excluded_for_median_spread": sum(
                1 for row in rows if row["minimum_observations_met"] and not row["median_spread_equals_one_tick"]
            ),
            "excluded_for_fraction": sum(
                1
                for row in rows
                if row["minimum_observations_met"]
                and row["median_spread_equals_one_tick"]
                and not row["fraction_threshold_met"]
            ),
            "minimum_observations": PROXY_MINIMUM_SPREAD_OBSERVATIONS,
            "theta": float(configuration["universe"]["theta_fraction_at_one_tick"]),
            "config_sha256": config_module.sha256_file(config_path),
        },
    )
    print(f"large-tick proxy: {len(subset)} of {len(rows)} scope symbols", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
