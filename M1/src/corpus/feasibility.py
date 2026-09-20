"""Data feasibility assessment per candidate (authored tri-state inputs).

The columns here are the *evidence-backed inputs* to the feasibility calculation; the
verdicts are recomputed and consistency-checked by ``m1/feasibility.py``. Nothing here
is inferred from a candidate's desirability.

Tri-state rule (ASM-0008): PASS = availability evidenced; FAIL = evidenced unavailable
for this candidate's requirement; BLOCKED = cannot be judged from available evidence.
"""

from .constants import UNKNOWN

COLUMNS = [
    "candidate_id", "live_feed", "historical_feed", "PIT_reconstructable",
    "L1_available", "L2_available", "L3_available", "queue_replay_possible",
    "timestamp_adequacy", "depth_source_id", "history_source_id",
    "PIT_source_id", "timestamp_source_id", "feasibility_note",
]

ROWS = []

_P, _F, _B = "PASS", "FAIL", "BLOCKED"


def add(candidate_id, live_feed, historical_feed, PIT_reconstructable, L1, L2, L3,
        queue_replay, timestamp_adequacy, depth_source_id, history_source_id,
        PIT_source_id, timestamp_source_id, note):
    ROWS.append(dict(
        candidate_id=candidate_id, live_feed=live_feed, historical_feed=historical_feed,
        PIT_reconstructable=PIT_reconstructable, L1_available=L1, L2_available=L2,
        L3_available=L3, queue_replay_possible=queue_replay,
        timestamp_adequacy=timestamp_adequacy, depth_source_id=depth_source_id,
        history_source_id=history_source_id, PIT_source_id=PIT_source_id,
        timestamp_source_id=timestamp_source_id, feasibility_note=note))


_CME_NOTE = ("Live full-depth MBO is verified; the historical order-level package, its cost and "
             "its timestamp semantics are not locked, so replay and PIT reconstruction are BLOCKED "
             "rather than PASS.")
_CME_ARGS = dict(
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_P,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0107",
    history_source_id="SRC-0123", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note=_CME_NOTE)

add("TUP-CME-ES-H1-QDEP-PAS", **_CME_ARGS)
add("TUP-CME-ES-H3-OFI-AGG", **_CME_ARGS)
add("TUP-CME-NQ-H3-OFI-AGG", **_CME_ARGS)
add("TUP-CME-WTI-H4-FLOWVOL-AGG", **_CME_ARGS)

add("TUP-CME-TSY-H2-QREPL-MIX",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_P,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0107",
    history_source_id="SRC-0123", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Same as the other CME rows, with the added complication that Treasury spread matching "
         "rules have changed by notice (EVD-0003), so a queue replay would have to be rule-versioned.")

_NQ_NOTE = ("Live TotalView depth is verified. Consolidated Tick History is Level 1 (EVD-0005) and "
            "cannot reconstruct individual order queues, so L1-only history is a verified FAIL for "
            "queue work while the order-level historical package remains BLOCKED.")

add("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_F,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0108",
    history_source_id="SRC-0109", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note=_NQ_NOTE + " L3_available records the verified fact that the accessible history product "
                    "carries no order-level data.")

add("TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_F,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0108",
    history_source_id="SRC-0109", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note=_NQ_NOTE)

add("TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG",
    live_feed=_P, historical_feed=_F, PIT_reconstructable=_F, L1=_P, L2=_F, L3=_F,
    queue_replay=_F, timestamp_adequacy=_B, depth_source_id="SRC-0108",
    history_source_id="SRC-0109", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Killed variant: the only history this row would use is the verified Level-1 product, so "
         "queue replay is a verified FAIL rather than BLOCKED.")

add("TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_F,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0108",
    history_source_id=UNKNOWN, PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="NOII existence is verified live; historical NOII depth/cost, auction print history and "
         "exact dissemination timestamp semantics are not locked. Auction matching is not "
         "continuous-book queue logic, so L3_available is recorded as FAIL for the mechanism.")

add("TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Fee schedule is verified but neither proprietary depth availability nor order-level "
         "history is locked for this project's access path, and no timestamp semantics are verified.")

add("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Dead on fees, so data-package work was not performed; fields stay BLOCKED rather than "
         "being filled with plausible vendor capabilities.")

add("TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Dead on fees; required L2/L3 schema was not locked in the M1-A pass.")

add("TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS",
    live_feed=_F, historical_feed=_B, PIT_reconstructable=_F, L1=_P, L2=_P, L3=_F,
    queue_replay=_F, timestamp_adequacy=_B, depth_source_id="SRC-0111",
    history_source_id="SRC-0118", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Killed by verified feed cadence: the documented book snapshot cadence is at least 0.5 s "
         "and levels are aggregate, so the 10-100 ms observation loop is a verified FAIL.")

add("TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_F,
    queue_replay=_F, timestamp_adequacy=_B, depth_source_id="SRC-0111",
    history_source_id="SRC-0118", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Live L2/trades are observable at the documented seconds-scale cadence; event-by-event "
         "historical replay and market-wide liquidation observability are not verified. Aggregate "
         "levels give no queue identifiers, so queue replay is FAIL for the mechanism.")

add("TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_P, L2=_P, L3=_F,
    queue_replay=_F, timestamp_adequacy=_B, depth_source_id="SRC-0111",
    history_source_id="SRC-0118", PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Funding/basis history and cross-venue hedge data are not locked.")

add("TUP-EUREX-FESX-H2H3-OFIQ-MIX",
    live_feed=_P, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id="SRC-0110",
    history_source_id=UNKNOWN, PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="EOBI order-book interface documentation is verified; historical acquisition, cost and "
         "access are not, and L1/L2/L3 availability is not characterised for this project.")

add("TUP-CBOE-USOPT-H5-SURFRV-MIX",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_F, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Options surface data, NBBO/proprietary depth and PIT greek derivation are not locked; "
         "queue replay is not the mechanism, recorded FAIL only to mean 'not applicable/not needed' "
         "— no economic conclusion is drawn from that cell.")

add("TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Required current access/fee/data facts were not verified in the M1-A pass.")

add("TUP-KALSHI-EVENT-H5-EVENTINF-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="API/fee/history schema not locked, and jurisdiction-specific access is unresolved "
         "(EVD-0016).")

add("TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Current primary access and execution facts insufficient.")

add("TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="No multi-venue synchronized-feed package is locked; NYSE/IEX exact 2026 fees and "
         "direct-feed history were outside the M1-A coverage.")

add("TUP-FX-ECN-H2H3-LEADLAG-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Venue/feed/access not specified tightly enough to assess any availability column.")

add("TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG",
    live_feed=_B, historical_feed=_B, PIT_reconstructable=_B, L1=_B, L2=_B, L3=_B,
    queue_replay=_B, timestamp_adequacy=_B, depth_source_id=UNKNOWN, history_source_id=UNKNOWN,
    PIT_source_id=UNKNOWN, timestamp_source_id=UNKNOWN,
    note="Broker and feed semantics undefined.")

for cid in ("TUP-METHOD-PASSIVE-TOUCHFILL", "TUP-GENERIC-CRYPTO-MICRO", "TUP-GENERIC-CME-QUEUE",
            "TUP-SYSTEMONE-HARDCORE-ENGINE", "TUP-JEV-HOSTED-LATENCY-UNMEASURED"):
    add(cid, _B, _B, _B, _B, _B, _B, _B, _B, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN,
        "Non-tuple registration row (method rule, universe definition, governance or technology "
        "admission). Data-feasibility columns are not meaningful and are recorded BLOCKED.")

BY_ID = {row["candidate_id"]: row for row in ROWS}