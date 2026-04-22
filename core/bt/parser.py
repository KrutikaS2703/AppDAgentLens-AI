import re
from typing import Iterable

BT_PATTERN = re.compile(
    r"BT\s+\[\d+]\s+Name\s*\[(?P<bt>[^]]+)](?:\s+Type\s+\[(?P<type>[^]]+)])?"
)

def parse_bt_lines(lines: Iterable[str]) -> dict:
    """
    Parse BT names from log lines and return aggregated BT metadata.
    """
    bt_summary = {}

    for line in lines:
        match = BT_PATTERN.search(line)
        if match:
            bt_name = match.group("bt")
            bt_type = match.group("type")
            if bt_name not in bt_summary:
                bt_summary[bt_name] = {
                    "count": 0,
                    "type": bt_type,
                    "_type_conflict": False,
                }

            bt_summary[bt_name]["count"] += 1
            if bt_type is not None:
                existing_type = bt_summary[bt_name].get("type")
                if existing_type is None:
                    bt_summary[bt_name]["type"] = bt_type
                elif existing_type != bt_type:
                    bt_summary[bt_name]["type"] = None
                    bt_summary[bt_name]["_type_conflict"] = True

    for bt_name, metadata in bt_summary.items():
        if metadata["_type_conflict"]:
            metadata["type"] = None

        metadata.pop("_type_conflict", None)

    return bt_summary
