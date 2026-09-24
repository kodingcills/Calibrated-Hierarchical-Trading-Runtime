"""Deterministic market-by-order replay engine and causal decision sampler.

One sequential pass over the raw tape, in file order:

1. decode every message and verify its frame length against the documented length;
2. maintain the displayed book for the development-scope symbols (orders by
   reference number, aggregated quantity per price level, best bid/ask);
3. emit the frozen causal decision grid (100 ms) and the delay sweep grid (1 s);
4. resolve future-state requests exactly, without interpolation;
5. reconcile the incremental levels against a rebuild from the order map;
6. accumulate every integrity counter in ``audit.py``.

Causality contract (frozen in the config, implemented here):

* A decision at grid time ``T`` uses the book state produced by every message
  that precedes it in file order and carries a timestamp ``<= T``. Emission
  happens at the first message with a timestamp ``> T``, before that message is
  applied. Messages that appear later in file order with an earlier timestamp are
  never retro-applied: they are counted as late/out-of-order events.
* A future state at ``t + Delta`` is the state after applying every message up to
  and including the first message whose timestamp reaches ``t + Delta``. If no
  two-sided book exists at that instant, the label is null with a status code.
* Labels whose horizon would extend past the end of the continuous session are
  marked and left null rather than filled from post-session state.

Nothing here repairs raw data. Impossible transitions are counted, reported and
(optionally) raised.
"""

from __future__ import annotations

import array
import heapq
import json
import os
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import audit as audit_module
from . import config as config_module
from . import features
from . import ingest
from . import labels

NS_PER_MS = 1_000_000

# Resolution-heap request kinds.
KIND_ROW_LABEL = 0
KIND_DELAY_ARRIVAL = 1
KIND_DELAY_EXIT = 2

# Arrival status codes for the delay sweep.
ARRIVAL_OK = 0
ARRIVAL_NO_STATE = 1
ARRIVAL_SESSION_ENDED = 2
# Sentinel while a delay arrival is still pending; replaced on resolution.
ARRIVAL_PENDING = 3

SIDE_BID = 0
SIDE_ASK = 1

# A decision row waits for the next real mid-price change, and every stale grid
# point that shares a midpoint waits on the same change. The wait list is stored in
# an array of 64-bit integers so that a whole session of stale grid points costs
# about a megabyte, and the safety cap is set far above any real session length so
# that no observation is dropped (a breach is counted and reported if it happens).
WATCH_ROW_SAFETY_CAP = 2_000_000

DECISION_SCHEMA = [
    ("ts_ns", np.int64),
    ("locate", np.int32),
    ("block_id", np.int16),
    ("best_bid_raw", np.int32),
    ("best_ask_raw", np.int32),
    ("bid_size", np.int32),
    ("ask_size", np.int32),
    ("mid2_raw", np.int64),
    ("spread_raw", np.int32),
    ("spread_ticks", np.float32),
    ("one_tick", np.bool_),
    ("imbalance", np.float32),
    ("time_since_last_event_ns", np.int64),
    ("events_in_prior_bucket", np.int32),
]

DELAY_SCHEMA = [
    ("ts_ns", np.int64),
    ("locate", np.int32),
    ("block_id", np.int16),
    ("imbalance", np.float32),
    ("mid2_raw", np.int64),
    ("spread_raw", np.int32),
]


class SymbolBook:
    """Displayed book state for one symbol, plus its decision-relevant counters."""

    __slots__ = (
        "locate",
        "symbol",
        "bids",
        "asks",
        "best_bid",
        "best_ask",
        "active",
        "deactivation_reason",
        "first_quote_ns",
        "last_event_ns",
        "bucket_id",
        "bucket_events",
        "watch_mid2",
        "watch_rows",
        "last_mid2",
        "mid_changes",
        "decision_points",
        "decision_states_missing",
        "first_decision_ns",
        "last_decision_ns",
    )

    def __init__(self, locate: int, symbol: str) -> None:
        self.locate = locate
        self.symbol = symbol
        self.bids: dict[int, int] = {}
        self.asks: dict[int, int] = {}
        self.best_bid: int | None = None
        self.best_ask: int | None = None
        self.active = True
        self.deactivation_reason = ""
        self.first_quote_ns: int | None = None
        self.last_event_ns: int | None = None
        self.bucket_id = -1
        self.bucket_events = 0
        self.watch_mid2: int | None = None
        self.watch_rows = array.array("q")
        self.last_mid2: int | None = None
        self.mid_changes = 0
        self.decision_points = 0
        self.decision_states_missing = 0
        self.first_decision_ns = 0
        self.last_decision_ns = 0

    def add(self, side: int, price: int, size: int) -> None:
        levels = self.bids if side == SIDE_BID else self.asks
        levels[price] = levels.get(price, 0) + size
        if side == SIDE_BID:
            if self.best_bid is None or price > self.best_bid:
                self.best_bid = price
        else:
            if self.best_ask is None or price < self.best_ask:
                self.best_ask = price

    def reduce(self, side: int, price: int, size: int) -> int:
        """Reduce a price level; returns the negative overshoot (0 when consistent)."""
        levels = self.bids if side == SIDE_BID else self.asks
        remaining = levels.get(price, 0) - size
        if remaining > 0:
            levels[price] = remaining
            return 0
        levels.pop(price, None)
        if side == SIDE_BID:
            if self.best_bid == price:
                self.best_bid = max(levels) if levels else None
        else:
            if self.best_ask == price:
                self.best_ask = min(levels) if levels else None
        return -remaining if remaining < 0 else 0

    def drop_symbol_orders_consistent(self) -> None:
        self.bids.clear()
        self.asks.clear()
        self.best_bid = None
        self.best_ask = None

    def mid2(self) -> int | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_bid + self.best_ask


class ChunkedParquetWriter:
    """Column store in bounded chunks, streamed to one Parquet file.

    Rows are appended in timestamp order, so a chunk can be written as soon as it is
    full without reordering anything. The bound is what keeps a whole-tape replay
    inside a small resident set: a table preallocated for every (symbol, grid
    instant) pair costs gigabytes before the first row is emitted, which starves a
    memory-tight host, and it couples the compute scope to a fixed capacity.
    """

    def __init__(self, path: str, schema: list[tuple[str, object]], chunk_rows: int) -> None:
        self.path = path
        self.chunk_rows = max(64, int(chunk_rows))
        self.schema = schema
        self.n = 0
        self.rows_written = 0
        self.chunks_written = 0
        self.columns = {name: np.zeros(self.chunk_rows, dtype=dtype) for name, dtype in schema}
        self.writer = None

    def add_column(self, name: str, dtype, initial=None) -> None:
        if initial is None:
            self.columns[name] = np.zeros(self.chunk_rows, dtype=dtype)
        else:
            self.columns[name] = np.full(self.chunk_rows, initial, dtype=dtype)

    @property
    def capacity(self) -> int:
        return self.chunk_rows

    def is_full(self) -> bool:
        return self.n >= self.chunk_rows

    def check_capacity(self) -> None:
        """The lag window must fit inside twice the chunk size."""
        if self.n >= 2 * self.chunk_rows:
            raise RuntimeError(
                f"{os.path.basename(self.path)}: {self.n} rows are waiting to be written in a "
                f"{self.chunk_rows}-row chunk; the write lag exceeds the chunk size"
            )

    def _arrow_schema(self) -> pa.Schema:
        """Explicit schema from the live numpy columns: the file schema must not depend
        on whichever rows happen to be in the first chunk, and it must include every
        column added after construction (labels, delay quotes)."""
        return pa.schema(
            [(name, pa.from_numpy_dtype(values.dtype)) for name, values in self.columns.items()]
        )

    def _table(self) -> pa.Table:
        return pa.table({name: values[: self.n] for name, values in self.columns.items()})

    def flush(self) -> None:
        """Write the whole chunk."""
        self.flush_upto(None)

    def flush_upto(self, cutoff_ts: int | None) -> int:
        """Write the leading rows older than ``cutoff_ts`` and keep the rest.

        A row may only be written once its future-state requests have resolved, so the
        write frontier trails the emission frontier by the longest label lag. Rows
        arrive in timestamp order, which makes the frontier a searchsorted on the
        timestamp column rather than a bookkeeping structure.
        """
        if self.n == 0:
            return 0
        if cutoff_ts is None:
            count = self.n
        else:
            timestamps = self.columns["ts_ns"][: self.n]
            count = int(np.searchsorted(timestamps, cutoff_ts, side="left"))
        if count <= 0:
            return 0
        if self.writer is None:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self.writer = pq.ParquetWriter(self.path, self._arrow_schema(), compression="zstd")
        self.writer.write_table(self._slice_table(count))
        self.rows_written += count
        self.chunks_written += 1
        remaining = self.n - count
        if remaining > 0:
            for values in self.columns.values():
                values[:remaining] = values[count : self.n]
                # The shifted-out tail is cleared so that a column the writer does not
                # touch for a new row can never inherit a stale value from an old one.
                values[remaining : self.n] = 0
        self.n = remaining
        return count

    def _slice_table(self, count: int) -> pa.Table:
        # The chunk is reused and shifted immediately after the write, so the slice is
        # copied into private buffers: writing a view of memory that is about to move is
        # how a parquet file ends up with unreadable pages.
        return pa.table(
            {name: np.array(values[:count], copy=True) for name, values in self.columns.items()}
        )

    def close(self) -> None:
        # The final chunk stays readable after the run (its rows are already written;
        # n is restored so the last chunk can be inspected); rows_written is the
        # authoritative total.
        remaining = self.n
        self.flush()
        self.n = remaining
        if self.writer is not None:
            self.writer.close()
            self.writer = None


def select_candidates(
    configuration: dict,
    summary: dict,
    directory: dict[int, dict],
) -> tuple[list[dict], list[dict]]:
    """Rank structurally eligible symbols by order-add count, or take a frozen list.

    This is a COMPUTE-SCOPE decision for the development sample, not universe
    membership. It uses no return, no imbalance-predictiveness and no P&L
    information; the default ranking variable is a message count. The frozen universe
    rule cannot be applied to a single day at all, because it requires a 60-trading-day
    causal lookback plus a point-in-time reference.

    When ``dev_scope.explicit_locates_manifest`` is set, the scope is the locate list
    in that manifest instead of the add-count ranking. The manifest is produced by a
    separate, frozen pass (``M2/src/universe_proxy.py``) whose ranking variable is the
    rule's own liquidity variable; the same eligibility sentences below still apply,
    so a locate in the manifest that fails them is excluded and reported rather than
    silently accepted.
    """
    scope_config = configuration["dev_scope"]
    price_floor_raw = int(configuration["price_floor_usd"] * configuration["price_scale"])
    add_counts = {int(k): v for k, v in summary["locate_add_counts"].items()}
    first_add_price = {int(k): v for k, v in summary["locate_first_add_price"].items()}

    candidates: list[dict] = []
    excluded: list[dict] = []
    for locate, entry in directory.items():
        reason = ""
        if scope_config["require_nasdaq_listed"] and entry["market_category"] not in ingest.NASDAQ_LISTED_CATEGORIES:
            reason = "NOT_NASDAQ_LISTED"
        elif scope_config["require_common_stock"] and entry["issue_classification"] != "C":
            reason = "NOT_COMMON_STOCK"
        elif scope_config["require_not_etp"] and entry["etp_flag"] == "Y":
            reason = "IS_ETP"
        elif entry["authenticity"] != "P":
            reason = "NOT_LIVE_AUTHENTICITY"
        elif locate not in add_counts:
            reason = "NO_ADD_MESSAGES"
        elif scope_config["require_price_floor"] and first_add_price.get(locate, 0) < price_floor_raw:
            reason = "FIRST_ADD_PRICE_BELOW_FLOOR"
        if reason:
            excluded.append({"locate": locate, "symbol": entry["symbol"], "reason": reason})
            continue
        candidates.append(
            {
                "locate": locate,
                "symbol": entry["symbol"],
                "add_count": add_counts[locate],
                "first_add_price_raw": first_add_price.get(locate, 0),
                "market_category": entry["market_category"],
                "issue_classification": entry["issue_classification"],
            }
        )

    manifest_path = scope_config.get("explicit_locates_manifest")
    if manifest_path:
        with open(config_module.repo_path(manifest_path), "r") as handle:
            manifest = json.load(handle)
        ordered = [int(entry["locate"]) for entry in manifest["scope_locates"]]
        by_locate = {row["locate"]: row for row in candidates}
        selected = []
        for locate in ordered:
            row = by_locate.pop(locate, None)
            if row is None:
                excluded.append({"locate": locate, "symbol": "", "reason": "MANIFEST_LOCATE_FAILS_ELIGIBILITY"})
                continue
            selected.append(row)
        for row in by_locate.values():
            excluded.append({"locate": row["locate"], "symbol": row["symbol"], "reason": "OUTSIDE_COMPUTE_SCOPE_MANIFEST"})
        for rank, row in enumerate(selected):
            row["rank"] = rank
        return selected, excluded

    candidates.sort(key=lambda row: (-row["add_count"], row["symbol"]))
    pool = int(scope_config["candidate_pool_size"])
    selected = candidates[:pool]
    for rank, row in enumerate(selected):
        row["rank"] = rank
    for rank, row in enumerate(candidates[pool:], start=pool):
        excluded.append({"locate": row["locate"], "symbol": row["symbol"], "reason": "OUTSIDE_COMPUTE_SCOPE_RANK"})
    return selected, excluded


class Replayer:
    def __init__(self, configuration: dict, summary: dict, directory: dict[int, dict]) -> None:
        self.configuration = configuration
        self.summary = summary
        self.directory = directory
        self.session_start = int(configuration["session"]["continuous_start_ns"])
        self.session_end = int(configuration["session"]["continuous_end_ns"])
        self.grid_ns = int(configuration["decisions"]["grid_ns"])
        self.delay_grid_ns = int(configuration["decisions"]["delay_grid_ns"])
        self.horizons_ns = [int(h) * NS_PER_MS for h in configuration["horizons_ms"]]
        self.delays_ns = [int(d) * NS_PER_MS for d in configuration["delay_ms"]]
        self.tick_raw = int(configuration["tick_raw"])
        self.price_scale = int(configuration["price_scale"])
        self.price_floor_raw = int(configuration["price_floor_usd"] * self.price_scale)
        self.scope_pool_size = int(configuration["dev_scope"]["candidate_pool_size"])
        self.block_ns = int(configuration["statistics"]["bootstrap"]["block_length_ns"])
        self.reconciliation_interval_ns = int(
            configuration["data_quality"]["book_audit_sample_interval_ns"]
        )
        self.fail_fast = bool(configuration["data_quality"].get("fail_fast_on_impossible_state", True))
        self.candidates, self.excluded = select_candidates(configuration, summary, directory)
        self.books: dict[int, SymbolBook] = {
            row["locate"]: SymbolBook(row["locate"], row["symbol"]) for row in self.candidates
        }
        self.active_books: list[SymbolBook] = list(self.books.values())
        self.orders: dict[int, tuple[int, int, int, int]] = {}
        self.heap: list[tuple] = []
        # Global index of the first row currently held in each chunk; used to refuse a
        # late resolution that would write into a chunk that has already been written.
        self.decisions_base_index = 0
        self.delay_rows_base_index = 0
        self.grid_dates = np.arange(
            self.session_start, self.session_end, self.grid_ns, dtype=np.int64
        )
        self.chunk_rows = int(configuration["decisions"]["buffer_rows_per_chunk"])
        self.flush_min_rows = int(configuration["decisions"].get("flush_min_rows", 65_536))
        # A row may only be written after every future-state request it created has
        # resolved, so the write frontier trails both the clock and the earliest
        # request that is still pending.
        self.flush_lag_ns = max(self.horizons_ns) + max(self.delays_ns)
        self.next_move_wait_ns = int(configuration["decisions"]["next_move_wait_ns"])
        self.late_watch_resolutions = 0
        self.late_label_resolutions = 0
        self.late_delay_resolutions = 0
        # The buffer must hold the whole pending window: rows emitted within
        # max(next_move_wait, flush_lag) of "now" cannot be written yet. A config that
        # cannot satisfy that is refused here rather than halfway through a tape.
        rows_per_second = len(self.candidates) * (1_000_000_000 / self.grid_ns)
        pending_window_rows = rows_per_second * (self.next_move_wait_ns / 1_000_000_000)
        required_rows = int(pending_window_rows) + self.flush_min_rows
        if self.chunk_rows < pending_window_rows + self.flush_min_rows:
            raise ValueError(
                f"decisions.buffer_rows_per_chunk={self.chunk_rows} cannot hold the pending "
                f"window of about {int(pending_window_rows)} rows implied by "
                f"next_move_wait_ns={self.next_move_wait_ns} and {len(self.candidates)} symbols "
                f"plus the {self.flush_min_rows}-row write batch "
                f"(a buffer of at least {required_rows} rows is implied)"
            )
        derived_dir = config_module.repo_path(config_module.derived_dir(configuration))
        self.decisions = ChunkedParquetWriter(
            os.path.join(derived_dir, "decisions.parquet"), DECISION_SCHEMA, self.chunk_rows
        )
        for horizon_ms in configuration["horizons_ms"]:
            self.decisions.add_column(f"mid2_future_{horizon_ms}ms", np.int64)
            self.decisions.add_column(f"ret_bps_{horizon_ms}ms", np.float32)
            self.decisions.add_column(f"direction_{horizon_ms}ms", np.int8)
            self.decisions.add_column(f"label_status_{horizon_ms}ms", np.int8)
        self.decisions.add_column("next_move_direction", np.int8)
        # The size of the next real mid-price change, in ``mid2`` raw units (i.e. twice
        # the price move), written on the same event as ``next_move_direction``. It is
        # the calibration target of the M2-2 Stoikov micro-price; it adds a column and
        # changes no existing column, so it cannot alter any earlier measurement.
        self.decisions.add_column("next_move_delta_raw", np.int32)
        self.decisions.add_column("next_move_resolved", np.bool_)
        self.delay_rows = ChunkedParquetWriter(
            os.path.join(derived_dir, "delay_decisions.parquet"), DELAY_SCHEMA, self.chunk_rows
        )
        for delay_ms in configuration["delay_ms"]:
            # Missing prices are -1 (a raw price of 0 is not a valid quote), so an
            # unresolved arrival or horizon can never be mistaken for a zero quote.
            self.delay_rows.add_column(f"entry_bid_{delay_ms}ms", np.int32, initial=-1)
            self.delay_rows.add_column(f"entry_ask_{delay_ms}ms", np.int32, initial=-1)
            self.delay_rows.add_column(f"arrival_status_{delay_ms}ms", np.int8)
            for horizon_ms in configuration["horizons_ms"]:
                self.delay_rows.add_column(f"fut_bid_{delay_ms}ms_{horizon_ms}ms", np.int32, initial=-1)
                self.delay_rows.add_column(f"fut_ask_{delay_ms}ms_{horizon_ms}ms", np.int32, initial=-1)
        self.audit = audit_module.TapeAudit(
            session_start_ns=self.session_start,
            session_end_ns=self.session_end,
            bucket_ns=self.grid_ns,
            gap_threshold_ns=1_000_000_000,
            tracked_locates=self.books.keys(),
        )
        for state in self.books.values():
            self.audit.symbols[state.locate].symbol = state.symbol
        self.crosscheck: dict[int, dict] = {
            locate: {
                "symbol": state.symbol,
                "locate": locate,
                "reconciliation_samples": 0,
                "bid_matches": 0,
                "ask_matches": 0,
                "spread_matches": 0,
                "unexplained_mismatches": 0,
            }
            for locate, state in self.books.items()
        }
        self.next_grid = self.session_start
        self.next_delay_grid = self.session_start
        self.last_emitted_grid = -1
        self.next_reconciliation = self.session_start
        # whole-tape counters kept as locals for speed, flushed into the audit at the end
        self.counters = {
            "messages": 0,
            "book_messages": 0,
            "reversals": 0,
            "max_reversal_ns": 0,
            "identical_ts": 0,
            "late_after_decision": 0,
            "exact_bucket_duplicates_full_tape": 0,
            "tuple_key_repeats_adjacent": 0,
            "book_messages_other_symbols": 0,
            "session_gaps": 0,
            "largest_gap_ns": 0,
            "duplicate_check_messages": 0,
        }

    # ------------------------------------------------------------------ emission
    def emit_decisions(self, grid_ts: int) -> None:
        # Push the write frontier first: every row whose labels are final goes out to
        # Parquet, so the buffer only ever holds the pending window.
        # Row groups are batched: flushing on every grid instant would produce a row
        # group per instant (hundreds of thousands of them, with the compression of a
        # table written in one piece lost). The buffer holds the pending window plus one
        # batch, which is why buffer_rows_per_chunk must exceed both.
        frontier = self.write_frontier(grid_ts)
        if self.decisions.n >= self.flush_min_rows:
            self.decisions.flush_upto(frontier)
            self.decisions_base_index = self.decisions.rows_written
        if self.delay_rows.n >= self.flush_min_rows:
            self.delay_rows.flush_upto(frontier)
            self.delay_rows_base_index = self.delay_rows.rows_written
        columns = self.decisions.columns
        index = self.decisions.n
        capacity = self.decisions.capacity
        block_id = (grid_ts - self.session_start) // self.block_ns
        column_ts = columns["ts_ns"]
        column_locate = columns["locate"]
        column_block = columns["block_id"]
        column_bid = columns["best_bid_raw"]
        column_ask = columns["best_ask_raw"]
        column_bid_size = columns["bid_size"]
        column_ask_size = columns["ask_size"]
        column_mid2 = columns["mid2_raw"]
        column_spread = columns["spread_raw"]
        column_spread_ticks = columns["spread_ticks"]
        column_one_tick = columns["one_tick"]
        column_imbalance = columns["imbalance"]
        column_staleness = columns["time_since_last_event_ns"]
        column_events = columns["events_in_prior_bucket"]
        next_move_direction_column = columns["next_move_direction"]
        next_move_delta_column = columns["next_move_delta_raw"]
        next_move_resolved_column = columns["next_move_resolved"]
        horizon_columns = [
            (
                columns[f"mid2_future_{horizon_ms}ms"],
                columns[f"ret_bps_{horizon_ms}ms"],
                columns[f"direction_{horizon_ms}ms"],
                columns[f"label_status_{horizon_ms}ms"],
                horizon_ns,
            )
            for horizon_ms, horizon_ns in zip(
                self.configuration["horizons_ms"], self.horizons_ns
            )
        ]
        is_delay_grid = (grid_ts - self.session_start) % self.delay_grid_ns == 0
        delay_columns = None
        delay_index = -1
        if is_delay_grid:
            delay_columns = self.delay_rows.columns
            delay_index = self.delay_rows.n
        prior_bucket = (grid_ts - 1) // self.grid_ns
        heap_push = heapq.heappush
        heap = self.heap

        for state in self.active_books:
            if not state.active:
                continue
            state.decision_points += 1
            best_bid = state.best_bid
            best_ask = state.best_ask
            if best_bid is None or best_ask is None:
                state.decision_states_missing += 1
                continue
            if index >= capacity:
                raise RuntimeError(
                    f"pending window exhausted the decision buffer at grid {grid_ts}: "
                    f"{capacity} rows are waiting for labels. Raise buffer_rows_per_chunk "
                    "or lower next_move_wait_ns."
                )
            mid2 = best_bid + best_ask
            q_bid = state.bids.get(best_bid, 0)
            q_ask = state.asks.get(best_ask, 0)
            value = features.imbalance(q_bid, q_ask, True)
            spread = best_ask - best_bid
            column_ts[index] = grid_ts
            column_locate[index] = state.locate
            column_block[index] = block_id
            column_bid[index] = best_bid
            column_ask[index] = best_ask
            column_bid_size[index] = q_bid
            column_ask_size[index] = q_ask
            column_mid2[index] = mid2
            column_spread[index] = spread
            column_spread_ticks[index] = spread / self.tick_raw
            column_one_tick[index] = spread == self.tick_raw
            column_imbalance[index] = np.nan if value is None else value
            column_staleness[index] = (
                -1 if state.last_event_ns is None else grid_ts - state.last_event_ns
            )
            column_events[index] = (
                state.bucket_events if state.bucket_id == prior_bucket else 0
            )
            global_row = self.decisions_base_index + index
            # Every per-row column is written explicitly: the chunk is reused, so a
            # column left untouched would carry the previous chunk row's value.
            next_move_direction_column[index] = 0
            next_move_delta_column[index] = 0
            next_move_resolved_column[index] = False
            for horizon_slot, (
                mid2_column,
                ret_column,
                direction_column,
                status_column,
                horizon_ns,
            ) in enumerate(horizon_columns):
                mid2_column[index] = 0
                ret_column[index] = 0.0
                direction_column[index] = 0
                status_column[index] = labels.LABEL_UNAVAILABLE
                if grid_ts + horizon_ns > self.session_end:
                    status_column[index] = labels.LABEL_SESSION_ENDED
                else:
                    # The horizon slot must travel with the request: every request for
                    # this row shares the row index, so the slot is the only thing that
                    # distinguishes the 100/250/500/1000 ms labels from each other.
                    heap_push(
                        heap,
                        (grid_ts + horizon_ns, KIND_ROW_LABEL, global_row, horizon_slot, state.locate),
                    )
            # The quotient is the next real mid-price change; every stale grid point
            # sharing a midpoint waits on the same change, so all of them are kept.
            if state.watch_mid2 != mid2:
                state.watch_mid2 = mid2
                del state.watch_rows[:]
            if len(state.watch_rows) >= WATCH_ROW_SAFETY_CAP:
                raise RuntimeError(
                    "next-mid-move wait list exceeded its safety cap; the cap is a "
                    "memory guard, not a sampling rule, and hitting it means the "
                    "midpoint has not moved for millions of grid points"
                )
            state.watch_rows.append(global_row)
            if state.first_decision_ns == 0:
                state.first_decision_ns = grid_ts
            state.last_decision_ns = grid_ts
            index += 1

            if delay_columns is not None:
                if delay_index >= self.delay_rows.capacity:
                    raise RuntimeError(
                        f"pending window exhausted the delay buffer at grid {grid_ts}"
                    )
                delay_columns["ts_ns"][delay_index] = grid_ts
                delay_columns["locate"][delay_index] = state.locate
                delay_columns["block_id"][delay_index] = block_id
                delay_columns["imbalance"][delay_index] = np.nan if value is None else value
                delay_columns["mid2_raw"][delay_index] = mid2
                delay_columns["spread_raw"][delay_index] = spread
                for delay_ms in self.configuration["delay_ms"]:
                    delay_columns[f"entry_bid_{delay_ms}ms"][delay_index] = -1
                    delay_columns[f"entry_ask_{delay_ms}ms"][delay_index] = -1
                    for horizon_ms in self.configuration["horizons_ms"]:
                        delay_columns[f"fut_bid_{delay_ms}ms_{horizon_ms}ms"][delay_index] = -1
                        delay_columns[f"fut_ask_{delay_ms}ms_{horizon_ms}ms"][delay_index] = -1
                for delay_index_within, delay_ns in enumerate(self.delays_ns):
                    status_column = delay_columns[f"arrival_status_{self.configuration['delay_ms'][delay_index_within]}ms"]
                    if grid_ts + delay_ns > self.session_end:
                        status_column[delay_index] = ARRIVAL_SESSION_ENDED
                    else:
                        status_column[delay_index] = ARRIVAL_PENDING
                        heap_push(
                            heap,
                            (
                                grid_ts + delay_ns,
                                KIND_DELAY_ARRIVAL,
                                self.delay_rows_base_index + delay_index,
                                delay_index_within,
                                state.locate,
                            ),
                        )
                delay_index += 1

        self.decisions.n = index
        if is_delay_grid:
            self.delay_rows.n = delay_index

    def write_frontier(self, grid_ts: int) -> int:
        """Latest timestamp a row may carry and still be written out.

        A row is held until every label it created could have resolved. Horizon labels
        resolve within one horizon; the next-mid-change label is given the declared
        window ``next_move_wait_ns``. A resolution that arrives after its row was written
        is not an error and does not rewrite data: it is counted (see
        ``late_label_resolutions`` / ``late_delay_resolutions`` / ``late_watch_resolutions``)
        and the row keeps its recorded status.
        """
        return grid_ts - self.next_move_wait_ns

    # ---------------------------------------------------------------- resolution
    def resolve(self, timestamp_ns: int) -> None:
        heap = self.heap
        columns = self.decisions.columns
        delay_columns = self.delay_rows.columns
        books = self.books
        delay_ms = self.configuration["delay_ms"]
        horizon_ms = self.configuration["horizons_ms"]
        session_end = self.session_end
        while heap and heap[0][0] < timestamp_ns:
            target, kind, row, slot, locate = heapq.heappop(heap)
            state = books[locate]
            if kind == KIND_ROW_LABEL:
                if row < self.decisions_base_index:
                    self.late_label_resolutions += 1
                    continue
                local = row - self.decisions_base_index
                horizon = horizon_ms[slot]
                mid2 = state.mid2()
                if mid2 is None:
                    columns[f"label_status_{horizon}ms"][local] = labels.LABEL_NO_FUTURE_STATE
                    continue
                decision_mid2 = columns["mid2_raw"][local]
                columns[f"mid2_future_{horizon}ms"][local] = mid2
                columns[f"ret_bps_{horizon}ms"][local] = labels.future_return_bps(decision_mid2, mid2)
                columns[f"direction_{horizon}ms"][local] = labels.direction(decision_mid2, mid2)
                columns[f"label_status_{horizon}ms"][local] = labels.LABEL_OK
            elif kind == KIND_DELAY_ARRIVAL:
                if row < self.delay_rows_base_index:
                    self.late_delay_resolutions += 1
                    continue
                local = row - self.delay_rows_base_index
                delay = delay_ms[slot]
                best_bid = state.best_bid
                best_ask = state.best_ask
                if best_bid is None or best_ask is None:
                    delay_columns[f"arrival_status_{delay}ms"][row] = ARRIVAL_NO_STATE
                    continue
                delay_columns[f"entry_bid_{delay}ms"][local] = best_bid
                delay_columns[f"entry_ask_{delay}ms"][local] = best_ask
                delay_columns[f"arrival_status_{delay}ms"][local] = ARRIVAL_OK
                for horizon_slot, horizon_ns in enumerate(self.horizons_ns):
                    if target + horizon_ns > session_end:
                        continue
                    heapq.heappush(
                        self.heap,
                        (
                            target + horizon_ns,
                            KIND_DELAY_EXIT,
                            row,
                            slot * len(horizon_ms) + horizon_slot,
                            locate,
                        ),
                    )
            else:  # KIND_DELAY_EXIT
                if row < self.delay_rows_base_index:
                    self.late_delay_resolutions += 1
                    continue
                local = row - self.delay_rows_base_index
                delay = delay_ms[slot // len(horizon_ms)]
                horizon = horizon_ms[slot % len(horizon_ms)]
                best_bid = state.best_bid
                best_ask = state.best_ask
                if best_bid is None or best_ask is None:
                    continue
                delay_columns[f"fut_bid_{delay}ms_{horizon}ms"][local] = best_bid
                delay_columns[f"fut_ask_{delay}ms_{horizon}ms"][local] = best_ask

    # ------------------------------------------------------------ reconciliation
    def reconcile(self) -> None:
        rebuilt: dict[int, dict[int, int]] = {}
        rebuilt_ask: dict[int, dict[int, int]] = {}
        for ref, (locate, price, side, size) in self.orders.items():
            target = rebuilt if side == SIDE_BID else rebuilt_ask
            levels = target.get(locate)
            if levels is None:
                levels = {}
                target[locate] = levels
            levels[price] = levels.get(price, 0) + size
        for locate, state in self.books.items():
            if not state.active:
                continue
            row = self.crosscheck[locate]
            row["reconciliation_samples"] += 1
            state_audit = self.audit.symbols[locate]
            state_audit.reconciliation_samples += 1
            expected_bids = {price: size for price, size in state.bids.items() if size > 0}
            expected_asks = {price: size for price, size in state.asks.items() if size > 0}
            actual_bids = rebuilt.get(locate, {})
            actual_asks = rebuilt_ask.get(locate, {})
            bid_ok = actual_bids == expected_bids
            ask_ok = actual_asks == expected_asks
            cached_bid = state.best_bid
            cached_ask = state.best_ask
            recomputed_bid = max(actual_bids) if actual_bids else None
            recomputed_ask = min(actual_asks) if actual_asks else None
            spread_ok = (
                (cached_bid is None and recomputed_bid is None)
                and (cached_ask is None and recomputed_ask is None)
            ) or (
                cached_bid == recomputed_bid
                and cached_ask == recomputed_ask
                and (cached_bid is None or cached_ask is None or cached_ask - cached_bid == recomputed_ask - recomputed_bid)
            )
            row["bid_matches"] += 1 if bid_ok else 0
            row["ask_matches"] += 1 if ask_ok else 0
            row["spread_matches"] += 1 if spread_ok else 0
            if not (bid_ok and ask_ok and spread_ok):
                row["unexplained_mismatches"] += 1
                state_audit.reconciliation_mismatches += 1

    # ----------------------------------------------------------------------- run
    def run(self, raw_path: str, limit_messages: int = 0) -> dict:
        configuration = self.configuration
        books = self.books
        orders = self.orders
        audit = self.audit
        counters = self.counters
        message_lengths = ingest.MSG_LENGTH
        header = ingest.HEADER
        u64 = ingest.U64
        u32 = ingest.U32
        session_start = self.session_start
        session_end = self.session_end
        grid_ns = self.grid_ns
        emit = self.emit_decisions
        resolve = self.resolve
        reconcile = self.reconcile
        fail_fast = self.fail_fast
        scope = books
        symbol_audit = audit.symbols
        detector = audit.detector
        detector_observe = detector.observe
        heap_push = heapq.heappush
        tick_raw = self.tick_raw
        max_order_size = 1 << 30
        adjacent_duplicates = 0
        previous_payload = b""
        previous_ts = None
        previous_symbol_ts: dict[int, int] = {}
        gaps: list[tuple[int, int]] = []
        session_events: list[tuple[int, str, str]] = []
        next_reconciliation = self.next_reconciliation
        next_grid = self.next_grid
        next_delay_grid = self.next_delay_grid
        last_emitted_grid = -1
        truncated = False
        started = time.time()

        def anomaly(locate: int, kind: str, magnitude: int = 1) -> None:
            record = symbol_audit.get(locate)
            if record is not None:
                record.anomalies[kind] = record.anomalies.get(kind, 0) + magnitude
            if fail_fast:
                raise RuntimeError(f"impossible book transition: {kind} for locate {locate}")

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
                    if truncated:
                        break
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
                    locate, tracking, ts_hi, ts_lo = header.unpack_from(buffer, base + 1)
                    timestamp = (ts_hi << 16) | ts_lo
                    counters["messages"] += 1
                    # Exact duplicate detection, whole tape: a byte-identical repeat of
                    # the immediately preceding frame, and a byte-identical payload
                    # inside the same aligned 100 ms bucket. Both are exact; neither
                    # assumes that a repeated (type, timestamp, tracking) key is a
                    # duplicate, because that tuple is demonstrably not unique.
                    payload = bytes(view[base : base + declared])
                    if payload == previous_payload:
                        adjacent_duplicates += 1
                    previous_payload = payload
                    if audit.detector_full.observe(timestamp, payload):
                        counters["exact_bucket_duplicates_full_tape"] += 1
                    if previous_ts is not None:
                        if timestamp < previous_ts:
                            counters["reversals"] += 1
                            delta = previous_ts - timestamp
                            if delta > counters["max_reversal_ns"]:
                                counters["max_reversal_ns"] = delta
                        elif timestamp == previous_ts:
                            counters["identical_ts"] += 1
                        elif (
                            timestamp - previous_ts > 1_000_000_000
                            and session_start <= previous_ts < session_end
                        ):
                            counters["session_gaps"] += 1
                            gap = timestamp - previous_ts
                            if gap > counters["largest_gap_ns"]:
                                counters["largest_gap_ns"] = gap
                            if len(gaps) < 1000:
                                gaps.append((previous_ts, timestamp))
                    if timestamp <= last_emitted_grid:
                        counters["late_after_decision"] += 1
                    in_scope = locate in scope
                    if in_scope:
                        record = symbol_audit[locate]
                        record.messages += 1
                        previous_symbol = previous_symbol_ts.get(locate)
                        if previous_symbol is not None:
                            if timestamp < previous_symbol:
                                record.reversals += 1
                                delta = previous_symbol - timestamp
                                if delta > record.max_reversal_ns:
                                    record.max_reversal_ns = delta
                            elif timestamp == previous_symbol:
                                record.identical_ts += 1
                        if timestamp <= last_emitted_grid:
                            record.late_after_decision += 1
                        previous_symbol_ts[locate] = timestamp
                        if detector_observe(timestamp, payload):
                            record.duplicates_bucket += 1
                        counters["duplicate_check_messages"] += 1
                    previous_ts = timestamp

                    # Causal emission and as-of resolution both happen before the
                    # current message is applied, and both use strict less-than on
                    # the current timestamp. A decision at G therefore sees every
                    # message with timestamp <= G that precedes it in file order, and
                    # a future state at t+Delta is read with the identical rule, so
                    # neither can see a partially applied timestamp.
                    if next_grid < timestamp and next_grid < session_end:
                        while next_grid < timestamp and next_grid < session_end:
                            if next_grid >= session_start:
                                emit(next_grid)
                                last_emitted_grid = next_grid
                            next_grid += grid_ns
                    resolve(timestamp)

                    resolved_scope = False
                    if in_scope:
                        state = books[locate]
                        if state.active:
                            if message_type == 0x41 or message_type == 0x46:  # A / F
                                ref = u64.unpack_from(buffer, base + 11)[0]
                                side = SIDE_BID if view[base + 19] == 0x42 else SIDE_ASK
                                size = u32.unpack_from(buffer, base + 20)[0]
                                price = u32.unpack_from(buffer, base + 32)[0]
                                if size >= max_order_size:
                                    anomaly(locate, "implausible_size", 1)
                                existing = orders.get(ref)
                                if existing is not None:
                                    anomaly(locate, "order_id_collision")
                                else:
                                    orders[ref] = (locate, price, side, size)
                                    state.add(side, price, size)
                                    if message_type == 0x41:
                                        symbol_audit[locate].adds += 1
                                    else:
                                        symbol_audit[locate].adds_mpid += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                            elif message_type == 0x45:  # E
                                ref = u64.unpack_from(buffer, base + 11)[0]
                                executed = u32.unpack_from(buffer, base + 19)[0]
                                entry = orders.get(ref)
                                if entry is None:
                                    anomaly(locate, "orphan_execute")
                                else:
                                    order_locate, price, side, size = entry
                                    overshoot = state.reduce(side, price, executed)
                                    if overshoot:
                                        anomaly(locate, "negative_remaining")
                                        orders.pop(ref, None)
                                    elif size - executed == 0:
                                        orders.pop(ref, None)
                                    else:
                                        orders[ref] = (order_locate, price, side, size - executed)
                                    symbol_audit[locate].executes += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                            elif message_type == 0x43:  # C
                                ref = u64.unpack_from(buffer, base + 11)[0]
                                executed = u32.unpack_from(buffer, base + 19)[0]
                                entry = orders.get(ref)
                                if entry is None:
                                    anomaly(locate, "orphan_execute_with_price")
                                else:
                                    order_locate, price, side, size = entry
                                    overshoot = state.reduce(side, price, executed)
                                    if overshoot:
                                        anomaly(locate, "negative_remaining")
                                        orders.pop(ref, None)
                                    elif size - executed == 0:
                                        orders.pop(ref, None)
                                    else:
                                        orders[ref] = (order_locate, price, side, size - executed)
                                    symbol_audit[locate].executes_with_price += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                            elif message_type == 0x58:  # X
                                ref = u64.unpack_from(buffer, base + 11)[0]
                                cancelled = u32.unpack_from(buffer, base + 19)[0]
                                entry = orders.get(ref)
                                if entry is None:
                                    anomaly(locate, "orphan_cancel")
                                else:
                                    order_locate, price, side, size = entry
                                    overshoot = state.reduce(side, price, cancelled)
                                    if overshoot:
                                        anomaly(locate, "cancel_oversized")
                                        orders.pop(ref, None)
                                    elif size - cancelled == 0:
                                        orders.pop(ref, None)
                                    else:
                                        orders[ref] = (order_locate, price, side, size - cancelled)
                                    symbol_audit[locate].cancels += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                            elif message_type == 0x44:  # D
                                ref = u64.unpack_from(buffer, base + 11)[0]
                                entry = orders.pop(ref, None)
                                if entry is None:
                                    anomaly(locate, "orphan_delete")
                                else:
                                    order_locate, price, side, size = entry
                                    state.reduce(side, price, size)
                                    symbol_audit[locate].deletes += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                            elif message_type == 0x55:  # U
                                original = u64.unpack_from(buffer, base + 11)[0]
                                replacement = u64.unpack_from(buffer, base + 19)[0]
                                shares = u32.unpack_from(buffer, base + 27)[0]
                                price = u32.unpack_from(buffer, base + 31)[0]
                                entry = orders.pop(original, None)
                                if entry is None:
                                    anomaly(locate, "orphan_replace")
                                else:
                                    order_locate, old_price, side, size = entry
                                    state.reduce(side, old_price, size)
                                    symbol_audit[locate].replaces += 1
                                    counters["book_messages"] += 1
                                    resolved_scope = True
                                    if replacement in orders:
                                        # Conservative handling: the replacement is not
                                        # invented, the original is removed as the spec
                                        # requires, and the collision is counted.
                                        anomaly(locate, "replace_duplicate_new_ref")
                                    else:
                                        orders[replacement] = (order_locate, price, side, shares)
                                        state.add(side, price, shares)
                            else:
                                counters["book_messages_other_symbols"] += 1

                            if resolved_scope:
                                record = symbol_audit[locate]
                                record.book_messages += 1
                                if state.last_event_ns is None or timestamp > state.last_event_ns:
                                    state.last_event_ns = timestamp
                                bucket = timestamp // grid_ns
                                if bucket != state.bucket_id:
                                    state.bucket_id = bucket
                                    state.bucket_events = 1
                                else:
                                    state.bucket_events += 1
                                if state.first_quote_ns is None and state.best_bid is not None and state.best_ask is not None:
                                    state.first_quote_ns = timestamp
                                    mid2 = state.best_bid + state.best_ask
                                    if mid2 < 2 * self.price_floor_raw:
                                        state.active = False
                                        state.deactivation_reason = "BELOW_PRICE_FLOOR"
                                        for ref in [r for r, o in orders.items() if o[0] == locate]:
                                            orders.pop(ref, None)
                                        state.drop_symbol_orders_consistent()
                                best_bid = state.best_bid
                                best_ask = state.best_ask
                                if best_bid is not None and best_ask is not None:
                                    if best_bid > best_ask:
                                        record.crossed_book_updates += 1
                                    elif best_bid == best_ask:
                                        record.locked_book_updates += 1
                                else:
                                    if session_start <= timestamp < session_end:
                                        record.empty_side_updates += 1
                                mid2 = state.mid2()
                                if (
                                    state.watch_rows
                                    and mid2 is not None
                                    and state.watch_mid2 is not None
                                    and mid2 != state.watch_mid2
                                ):
                                    direction_column = self.decisions.columns["next_move_direction"]
                                    delta_column = self.decisions.columns["next_move_delta_raw"]
                                    resolved_column = self.decisions.columns["next_move_resolved"]
                                    direction = labels.next_mid_move_direction(state.watch_mid2, mid2)
                                    delta = int(mid2 - state.watch_mid2)
                                    for watch_row in state.watch_rows:
                                        local = watch_row - self.decisions_base_index
                                        if local < 0:
                                            # The row was written before its next-mid-change
                                            # label could be resolved; it keeps
                                            # next_move_resolved = false and is counted.
                                            self.late_watch_resolutions += 1
                                            continue
                                        direction_column[local] = direction
                                        delta_column[local] = delta
                                        resolved_column[local] = True
                                    del state.watch_rows[:]
                                    state.watch_mid2 = None
                                if mid2 != state.last_mid2:
                                    state.mid_changes += 1
                                    state.last_mid2 = mid2
                    elif message_type in ingest.BOOK_MODIFYING:
                        counters["book_messages_other_symbols"] += 1

                    if message_type == 0x53:
                        code = bytes(view[base + 11 : base + 12]).decode("ascii")
                        session_events.append(
                            (timestamp, code, ingest.SYSTEM_EVENT_NAME.get(code.encode("ascii"), "unrecognised"))
                        )
                        audit.session_events.append((timestamp, code, ingest.SYSTEM_EVENT_NAME.get(code.encode("ascii"), "unrecognised")))

                    if limit_messages and counters["messages"] >= limit_messages:
                        truncated = True
                        break

                    if timestamp >= next_reconciliation:
                        while next_reconciliation <= timestamp:
                            reconcile()
                            next_reconciliation += self.reconciliation_interval_ns

                    position += ingest.FRAME_PREFIX + declared
                view.release()
                del buffer[:position]
                position = 0
                if truncated:
                    break
        if not truncated:
            ingest.check_no_trailing_bytes(buffer)

        self.decisions.close()
        self.delay_rows.close()
        elapsed = time.time() - started
        self.next_grid = next_grid
        self.next_delay_grid = next_delay_grid
        self.last_emitted_grid = last_emitted_grid

        for state in self.books.values():
            self.audit.symbols[state.locate].live_orders_end = sum(
                1 for order in orders.values() if order[0] == state.locate
            )
        counters["exact_adjacent_duplicates"] = adjacent_duplicates
        counters["tuple_key_repeats_adjacent"] = self.summary.get("adjacent_duplicates", 0)
        audit.exact_adjacent_duplicates = adjacent_duplicates
        audit.exact_bucket_duplicates_full_tape = counters["exact_bucket_duplicates_full_tape"]
        audit.tuple_key_repeats_adjacent = counters["tuple_key_repeats_adjacent"]
        audit.messages = counters["messages"]
        audit.book_messages = counters["book_messages"]
        audit.reversals = counters["reversals"]
        audit.max_reversal_ns = counters["max_reversal_ns"]
        audit.identical_ts = counters["identical_ts"]
        audit.late_after_decision = counters["late_after_decision"]
        audit.gap_count = counters["session_gaps"]
        audit.largest_gap_ns = counters["largest_gap_ns"]
        audit.gaps = gaps
        return {
            "elapsed_seconds": round(elapsed, 1),
            "truncated": truncated,
            "messages": counters["messages"],
            "book_messages_scope": counters["book_messages"],
            "book_messages_other_symbols": counters["book_messages_other_symbols"],
            "decision_rows": int(self.decisions.rows_written),
            "delay_rows": int(self.delay_rows.rows_written),
            "decision_parquet_chunks": int(self.decisions.chunks_written),
            "delay_parquet_chunks": int(self.delay_rows.chunks_written),
            "candidate_symbols": [row["symbol"] for row in self.candidates],
            "active_symbols": sorted(state.symbol for state in self.books.values() if state.active),
            "late_watch_resolutions": self.late_watch_resolutions,
            "late_label_resolutions": self.late_label_resolutions,
            "late_delay_resolutions": self.late_delay_resolutions,
            "scope_deactivations": [
                {"symbol": state.symbol, "reason": state.deactivation_reason}
                for state in self.books.values()
                if not state.active
            ],
            "orders_live_end_of_day": len(orders),
            "counters": counters,
        }


def evaluate_quality_limits(configuration: dict, replayer: Replayer) -> dict:
    """Evaluate the binding data-quality limits frozen in the config.

    A breach marks the run DATA_INVALID. Nothing is repaired, no limit is relaxed
    after seeing the numbers.
    """
    limits = configuration["data_quality"]["binding_limits"]
    audit = replayer.audit
    scope_book_updates = sum(state.book_messages for state in audit.symbols.values())
    orphans = 0
    negative = 0
    collisions = 0
    crossed = 0
    for state in audit.symbols.values():
        for kind, count in state.anomalies.items():
            if kind.startswith("orphan_"):
                orphans += count
            elif kind in ("negative_remaining", "cancel_oversized", "implausible_size"):
                negative += count
            elif kind in ("order_id_collision", "replace_duplicate_new_ref"):
                collisions += count
        crossed += state.crossed_book_updates
    total_messages = max(1, audit.messages)
    orphan_fraction = orphans / max(1, scope_book_updates)
    backwards_fraction = audit.reversals / total_messages
    crossed_fraction = crossed / max(1, scope_book_updates)
    checks = [
        {
            "check": "orphan_event_fraction",
            "value": orphan_fraction,
            "limit": limits["max_orphan_event_fraction"],
            "breached": orphan_fraction > limits["max_orphan_event_fraction"],
        },
        {
            "check": "negative_size_events",
            "value": negative,
            "limit": limits["max_negative_size_events"],
            "breached": negative > limits["max_negative_size_events"],
        },
        {
            "check": "order_id_collisions",
            "value": collisions,
            "limit": limits["max_order_id_collisions"],
            "breached": collisions > limits["max_order_id_collisions"],
        },
        {
            "check": "backwards_timestamp_fraction",
            "value": backwards_fraction,
            "limit": limits["max_backwards_timestamp_fraction"],
            "breached": backwards_fraction > limits["max_backwards_timestamp_fraction"],
        },
        {
            "check": "crossed_book_update_fraction",
            "value": crossed_fraction,
            "limit": limits["max_crossed_book_update_fraction"],
            "breached": crossed_fraction > limits["max_crossed_book_update_fraction"],
        },
    ]
    report_only = {
        "late_after_decision": audit.late_after_decision,
        "locked_book_updates": sum(s.locked_book_updates for s in audit.symbols.values()),
        "empty_side_updates": sum(s.empty_side_updates for s in audit.symbols.values()),
        "identical_timestamp_messages": audit.identical_ts,
        "duplicates_within_bucket": audit.detector.duplicates,
        "sequence_substitute_regressions": audit.tracking_regressions,
        "reconciliation_mismatches": sum(s.reconciliation_mismatches for s in audit.symbols.values()),
    }
    breached = [check for check in checks if check["breached"]]
    return {
        "verdict": "DATA_INVALID" if breached else "DATA_VALID",
        "checks": checks,
        "report_only": report_only,
        "orphans": orphans,
        "negative_size_events": negative,
        "order_id_collisions": collisions,
        "crossed_book_updates": crossed,
        "scope_book_updates": scope_book_updates,
    }


def main(argv: list[str] | None = None) -> int:
    """Stage 2: replay the tape, emit derived state, audits and the verdict."""
    import argparse

    parser = argparse.ArgumentParser(description="Replay a raw ITCH tape (stage 2).")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0.yaml")
    parser.add_argument("--limit-messages", type=int, default=0, help="debug: stop after N messages")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    raw_path = config_module.repo_path(
        os.path.join(configuration["paths"]["raw_dir"], configuration["dataset"]["raw_files"][0])
    )
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    with open(os.path.join(derived, "ingest_summary.json"), "r") as handle:
        summary = json.load(handle)
    directory = ingest.read_symbol_directory(raw_path)

    replayer = Replayer(configuration, summary, directory)
    replay = replayer.run(raw_path, arguments.limit_messages)
    limits = evaluate_quality_limits(configuration, replayer)

    decisions_path = os.path.join(derived, "decisions.parquet")
    delay_path = os.path.join(derived, "delay_decisions.parquet")

    data_quality = config_module.ensure_dirs(configuration, "data_quality")
    date = configuration["dataset"]["coverage_date"]
    audit_module.write_timestamp_audit(
        os.path.join(data_quality, "timestamp_audit.csv"), date, replayer.audit
    )
    audit_module.write_sequence_audit(
        os.path.join(data_quality, "sequence_gap_audit.csv"), date, replayer.audit
    )
    audit_module.write_ordering_audit(
        os.path.join(data_quality, "ordering_anomalies.csv"), date, replayer.audit
    )
    audit_module.write_book_audit(
        os.path.join(data_quality, "book_reconstruction_audit.csv"),
        date,
        replayer.audit,
        "RECONSTRUCTION_CONSISTENT" if limits["verdict"] == "DATA_VALID" else "RECONSTRUCTION_FLAGGED",
    )
    crosscheck_rows = []
    for row in replayer.crosscheck.values():
        samples = max(1, row["reconciliation_samples"])
        crosscheck_rows.append(
            {
                **row,
                "bid_match_rate": row["bid_matches"] / samples,
                "ask_match_rate": row["ask_matches"] / samples,
                "spread_match_rate": row["spread_matches"] / samples,
            }
        )
    audit_module.write_book_crosscheck(
        os.path.join(data_quality, "book_crosscheck.csv"),
        date,
        crosscheck_rows,
        "INTERNAL_ORDER_MAP_REBUILD",
        "No provider BBO/MBP artifact is contained in the TotalView-ITCH product, so the "
        "independent representation used here is a full rebuild of every price level from the "
        "order map, compared against the incrementally maintained levels and best quotes. "
        "A provider BBO cross-check remains CALCULATION_BLOCKED on a second data product.",
    )

    scope_rows = [
        {
            "locate": row["locate"],
            "symbol": row["symbol"],
            "rank": row["rank"],
            "add_count": row["add_count"],
            "first_add_price_usd": row["first_add_price_raw"] / configuration["price_scale"],
            "market_category": row["market_category"],
            "issue_classification": row["issue_classification"],
            "scope": configuration["dev_scope"].get("label", "DEVELOPMENT_SCOPE_NOT_UNIVERSE_MEMBERSHIP"),
        }
        for row in replayer.candidates
    ]
    import csv as csv_module

    with open(os.path.join(data_quality, "scope_manifest.csv"), "w", newline="") as handle:
        writer = csv_module.DictWriter(handle, fieldnames=list(scope_rows[0].keys()))
        writer.writeheader()
        for row in scope_rows:
            writer.writerow(row)
    with open(os.path.join(data_quality, "scope_exclusions.csv"), "w", newline="") as handle:
        writer = csv_module.DictWriter(handle, fieldnames=["locate", "symbol", "reason"])
        writer.writeheader()
        for row in replayer.excluded:
            writer.writerow(row)

    payload = {
        "dataset_id": configuration["dataset"]["dataset_id"],
        "coverage_date": date,
        "replay": replay,
        "quality_limits": limits,
        "decision_rows": int(replayer.decisions.rows_written),
        "delay_rows": int(replayer.delay_rows.rows_written),
        "derived": {
            "decisions_parquet": os.path.relpath(decisions_path, config_module.REPO_ROOT),
            "delay_decisions_parquet": os.path.relpath(delay_path, config_module.REPO_ROOT),
        },
        "run_status": limits["verdict"],
    }
    config_module.write_json(os.path.join(derived, "replay_summary.json"), payload)
    print(json.dumps({"verdict": limits["verdict"], "replay": replay, "checks": limits["checks"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
