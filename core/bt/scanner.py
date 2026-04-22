from pathlib import Path
from core.bt.parser import parse_bt_lines
from core.bt.dropped_bt import scan_dropped_bts


def run_bt_analysis(log_dir: str) -> dict:
    """
    Scan BusinessTransactions*.log files and return BT summary
    """

    base = Path(log_dir)
    if not base.exists():
        raise FileNotFoundError(log_dir)

    bt_summary = {}

    # =============================
    # Normal BT counting
    # =============================
    for log_file in base.glob("BusinessTransactions*.log"):
        with log_file.open(errors="ignore") as f:
            file_summary = parse_bt_lines(f)

        for bt, metadata in file_summary.items():
            if bt not in bt_summary:
                bt_summary[bt] = {"count": 0, "type": metadata.get("type")}

            bt_summary[bt]["count"] += metadata["count"]
            if metadata.get("type") and not bt_summary[bt].get("type"):
                bt_summary[bt]["type"] = metadata["type"]

    # =============================
    # ✅ NEW: Dropped BT parsing
    # =============================
    dropped_bt_counts = scan_dropped_bts(log_dir)

    sorted_bt_summary = dict(
        sorted(bt_summary.items(), key=lambda item: -item[1]["count"])
    )

    # =============================
    # Final result
    # =============================
    return {
        "bt_counts": dict(
            (bt, metadata["count"])
            for bt, metadata in sorted_bt_summary.items()
        ),
        "bt_details": sorted_bt_summary,
        "total_bt_events": sum(metadata["count"] for metadata in bt_summary.values()),
        "unique_bts": len(bt_summary),

        # 👇 NEW FIELDS (used by UI)
        "dropped_bt_counts": dict(
            sorted(dropped_bt_counts.items(), key=lambda item: -item[1])
        ),
        "total_dropped_bts": sum(dropped_bt_counts.values()),
    }
    