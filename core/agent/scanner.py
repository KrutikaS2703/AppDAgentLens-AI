
def run_agent_analysis(log_dir: str) -> dict:
    """
    Scan JavaAgent logs and return summary
    """
    import os
    import re
    import fnmatch
    from datetime import datetime

    ts_pat = re.compile(
        r"\]\s+(\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3})"
    )
    ts_fmt = "%d %b %Y %H:%M:%S,%f"
    min_ts = datetime.min

    def parse_line_timestamp(line: str):
        match = ts_pat.search(line)
        if not match:
            return min_ts
        try:
            return datetime.strptime(match.group(1), ts_fmt)
        except ValueError:
            return min_ts

    def choose_latest_match(log_files: list, matcher):
        best_match = None
        best_key = (min_ts, float("-inf"), -1)

        for log_file in log_files:
            try:
                file_mtime = os.path.getmtime(log_file)
            except OSError:
                file_mtime = float("-inf")

            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        payload = matcher(line)
                        if payload is None:
                            continue

                        candidate_key = (parse_line_timestamp(line), file_mtime, line_num)
                        if candidate_key >= best_key:
                            best_key = candidate_key
                            best_match = {
                                "line": line.strip(),
                                "line_num": line_num,
                                "file": os.path.relpath(log_file, log_dir),
                                "full_path": log_file,
                                "timestamp": candidate_key[0].strftime(ts_fmt) if candidate_key[0] != min_ts else None,
                            }
                            best_match.update(payload)
            except Exception:
                continue

        return best_match

    def extract_agent_checkpoints(log_files: list) -> dict:
        debug_logger_match = choose_latest_match(
            log_files,
            lambda line: {
                "status": True,
                "details": "Logger DEBUG setting found in agent logs.",
            } if re.search(r"\blog(?:ger| level)?\b.*\bDEBUG\b|\bDEBUG\b.*\blog(?:ger| level)?\b", line, re.IGNORECASE) else None,
        )

        disable_agent_match = choose_latest_match(
            log_files,
            lambda line: (
                {
                    "status": value == "true",
                    "value": value,
                    "details": "Latest disable-agent setting is true; agent is disabled." if value == "true" else "Latest disable-agent setting is false; agent is not disabled.",
                }
            ) if (match := re.search(r"disable-agent\s*=\s*(true|false)", line, re.IGNORECASE)) and (value := match.group(1).lower()) else None,
        )

        def pojo_matcher(line: str):
            if "POJORuleApplier" not in line:
                return None
            enabled = "monitoring is enabled" in line.lower()
            disabled = "monitoring is disabled" in line.lower()
            if not enabled and not disabled:
                return None
            return {
                "status": enabled and not disabled,
                "details": "POJO monitoring is enabled." if enabled and not disabled else "POJO monitoring is disabled.",
            }

        def servlet_matcher(line: str):
            if "ServletEntryPointDelegate" not in line:
                return None
            match = re.search(r"Servlet monitoring enabled\s*=\s*(true|false)", line, re.IGNORECASE)
            if not match:
                return None
            enabled = match.group(1).lower() == "true"
            return {
                "status": enabled,
                "value": match.group(1).lower(),
                "details": "Servlet monitoring is enabled." if enabled else "Servlet monitoring is disabled.",
            }

        def jms_matcher(line: str):
            if "JMSEntryPointDelegate" not in line:
                return None
            lowered = line.lower()
            if "jms monitoring is enabled" in lowered:
                return {
                    "status": True,
                    "details": "JMS monitoring is enabled.",
                }
            if "jms monitoring is disabled" in lowered:
                return {
                    "status": False,
                    "details": "JMS monitoring is disabled.",
                }
            match = re.search(r"JMS monitoring .*?=\s*(true|false)", line, re.IGNORECASE)
            if not match:
                return None
            enabled = match.group(1).lower() == "true"
            return {
                "status": enabled,
                "value": match.group(1).lower(),
                "details": "JMS monitoring is enabled." if enabled else "JMS monitoring is disabled.",
            }

        pojo_match = choose_latest_match(log_files, pojo_matcher)
        servlet_match = choose_latest_match(log_files, servlet_matcher)
        jms_match = choose_latest_match(log_files, jms_matcher)

        jmx_domains_match = choose_latest_match(
            log_files,
            lambda line: (
                {
                    "domains": [
                        item.strip()
                        for item in match.group(1).split(",")
                        if item.strip()
                    ],
                    "details": "Latest discovered JMX domains.",
                }
            ) if (match := re.search(r"The following domains were discovered\s*\[(.*?)\]", line, re.IGNORECASE)) else None,
        )

        checkpoints = [
            {
                "key": "debug_logger",
                "label": "Logger level shows DEBUG",
                "status": bool(debug_logger_match and debug_logger_match.get("status")),
                "details": debug_logger_match.get("details") if debug_logger_match else "No DEBUG logger line found in agent logs.",
                "match": debug_logger_match,
            },
            {
                "key": "disable_agent",
                "label": "disable-agent=true in latest matched line",
                "status": bool(disable_agent_match and disable_agent_match.get("status")),
                "details": disable_agent_match.get("details") if disable_agent_match else "No disable-agent line found in agent logs.",
                "match": disable_agent_match,
            },
            {
                "key": "pojo_entry_point",
                "label": "POJO entry point monitoring enabled",
                "status": bool(pojo_match and pojo_match.get("status")),
                "details": pojo_match.get("details") if pojo_match else "No POJO monitoring line found in agent logs.",
                "match": pojo_match,
            },
            {
                "key": "servlet_entry_point",
                "label": "Servlet entry point monitoring enabled",
                "status": bool(servlet_match and servlet_match.get("status")),
                "details": servlet_match.get("details") if servlet_match else "No Servlet monitoring line found in agent logs.",
                "match": servlet_match,
            },
            {
                "key": "jms_entry_point",
                "label": "JMS entry point monitoring enabled",
                "status": bool(jms_match and jms_match.get("status")),
                "details": jms_match.get("details") if jms_match else "No JMS monitoring line found in agent logs.",
                "match": jms_match,
            },
        ]

        return {
            "items": checkpoints,
            "jmx_domains": jmx_domains_match.get("domains", []) if jmx_domains_match else [],
            "jmx_domains_match": jmx_domains_match,
        }

    def normalize_error_line(line: str) -> str:
        """
        Normalize error lines to group repetitive errors.
        Handles agent log format: [thread] DD Mon YYYY HH:MM:SS,ms  LEVEL ClassName - message
        """
        text = line.strip()
        # Strip full agent log header: [thread] DD Mon YYYY HH:MM:SS,ms  LEVEL
        text = re.sub(
            r"^\[[^\]]*\]\s+\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\w+\s+",
            "", text
        )
        # Strip ISO timestamp variants: [2026-02-04 13:27:51,002] or 2026-02-04T13:27:51,002
        text = re.sub(r"^\[?\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:,\d+)?\]?\s*", "", text)
        # Strip bare time: HH:MM:SS,ms
        text = re.sub(r"^\d{2}:\d{2}:\d{2}(?:,\d+)?\s*", "", text)
        # Strip any remaining leading [anything]
        text = re.sub(r"^\[[^\]]*\]\s*", "", text)
        # Remove log level keywords
        text = re.sub(r"\b(ERROR|WARN|INFO|DEBUG|TRACE|FATAL)\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def is_error_level_line(line: str) -> bool:
        """
        Return True only if the log level token is ERROR.
        """
        return bool(re.search(
            r"^\[[^\]]+\]\s+\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3}\s+ERROR\b",
            line
        ))

    def extract_error_summaries(log_files: list) -> dict:
        """
        Extract ERROR lines and keep the latest occurrence per unique error per file.
        """
        errors_by_file = {}
        total_errors = 0
        unique_errors = 0

        for log_file in log_files:
            file_name = os.path.basename(log_file)
            relative_path = os.path.relpath(log_file, log_dir)
            file_error_map = {}
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if is_error_level_line(line):
                            total_errors += 1
                            signature = normalize_error_line(line)
                            if not signature:
                                signature = line.strip().lower()
                            entry = file_error_map.get(signature)
                            if entry:
                                entry["line"] = line.strip()
                                entry["line_num"] = line_num
                                entry["occurrences"] += 1
                            else:
                                file_error_map[signature] = {
                                    "line": line.strip(),
                                    "line_num": line_num,
                                    "file": relative_path,
                                    "file_name": file_name,
                                    "full_path": log_file,
                                    "occurrences": 1,
                                }
                if file_error_map:
                    errors_by_file[relative_path] = list(file_error_map.values())
                    unique_errors += len(file_error_map)
            except Exception:
                continue

        def _short_label(raw_line: str) -> str:
            """Return full log line label while removing only timestamp text."""
            text = raw_line.rstrip("\n")
            # Remove leading thread marker like: [thread-name]
            text = re.sub(r"^\[[^\]]+\]\s*", "", text)
            # Remove only the first timestamp token like: 20 Apr 2026 10:01:02,123
            text = re.sub(
                r"\b\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3}\b\s*",
                "",
                text,
                count=1,
            )
            # Remove leading level token after timestamp/thread cleanup.
            text = re.sub(r"^(?:ERROR|WARN)\b\s*", "", text, flags=re.IGNORECASE)
            return text.strip()

        global_error_map = {}
        for relative_path, entries in errors_by_file.items():
            for entry in entries:
                raw_line = entry.get("line", "")
                sig = normalize_error_line(raw_line) or raw_line.lower()
                if sig not in global_error_map:
                    global_error_map[sig] = {
                        "label": _short_label(raw_line),
                        "occurrences": 0,
                    }
                global_error_map[sig]["occurrences"] += entry.get("occurrences", 1)

        error_type_counts = sorted(
            [
                {
                    "label": v["label"],
                    "occurrences": v["occurrences"],
                }
                for v in global_error_map.values()
            ],
            key=lambda x: x["occurrences"],
            reverse=True,
        )

        return {
            "total_errors": total_errors,
            "unique_errors": len(global_error_map),
            "errors_by_file": errors_by_file,
            "error_type_counts": error_type_counts,
        }


    def extract_warn_summaries(log_files: list) -> dict:
        """
        Extract WARN lines per file and build global warn-type frequency counts.
        """
        def is_warn_level_line(line: str) -> bool:
            return bool(re.search(
                r"^\[[^\]]+\]\s+\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3}\s+WARN\b",
                line
            ))

        warns_by_file = {}
        total_warns = 0

        for log_file in log_files:
            file_name = os.path.basename(log_file)
            relative_path = os.path.relpath(log_file, log_dir)
            file_warn_map = {}
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if is_warn_level_line(line):
                            total_warns += 1
                            signature = normalize_error_line(line)
                            if not signature:
                                signature = line.strip().lower()
                            entry = file_warn_map.get(signature)
                            if entry:
                                entry["line"] = line.strip()
                                entry["line_num"] = line_num
                                entry["occurrences"] += 1
                            else:
                                file_warn_map[signature] = {
                                    "line": line.strip(),
                                    "line_num": line_num,
                                    "file": relative_path,
                                    "file_name": file_name,
                                    "full_path": log_file,
                                    "occurrences": 1,
                                }
                if file_warn_map:
                    warns_by_file[relative_path] = list(file_warn_map.values())
            except Exception:
                continue

        def _short_label(raw_line: str) -> str:
            text = raw_line.rstrip("\n")
            # Remove leading thread marker like: [thread-name]
            text = re.sub(r"^\[[^\]]+\]\s*", "", text)
            # Remove only the first timestamp token like: 20 Apr 2026 10:01:02,123
            text = re.sub(
                r"\b\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3}\b\s*",
                "",
                text,
                count=1,
            )
            # Remove leading level token after timestamp/thread cleanup.
            text = re.sub(r"^(?:ERROR|WARN)\b\s*", "", text, flags=re.IGNORECASE)
            return text.strip()

        global_warn_map = {}
        for relative_path, entries in warns_by_file.items():
            for entry in entries:
                raw_line = entry.get("line", "")
                sig = normalize_error_line(raw_line) or raw_line.lower()
                if sig not in global_warn_map:
                    global_warn_map[sig] = {
                        "label": _short_label(raw_line),
                        "occurrences": 0,
                    }
                global_warn_map[sig]["occurrences"] += entry.get("occurrences", 1)

        warn_type_counts = sorted(
            [{"label": v["label"], "occurrences": v["occurrences"]} for v in global_warn_map.values()],
            key=lambda x: x["occurrences"],
            reverse=True,
        )

        return {
            "total_warns": total_warns,
            "unique_warns": len(global_warn_map),
            "warns_by_file": warns_by_file,
            "warn_type_counts": warn_type_counts,
        }

    def extract_registered_business_transactions(log_files: list) -> list:
        """
        Extract unique pre-registered business transactions from agent logs.
        """
        bt_pattern = re.compile(
            r"Found pre-registered business transaction:\s*(?P<bt_id>\d+)\s+"
            r"for Business Transaction\s*\[(?P<bt_name>[^\]]+)\]\s+"
            r"Entry Point Type\s*\[(?P<entry_point_type>[^\]]+)\]",
            re.IGNORECASE
        )

        unique_bts = {}

        for log_file in log_files:
            file_name = os.path.basename(log_file)
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        match = bt_pattern.search(line)
                        if not match:
                            continue

                        bt_id = match.group("bt_id").strip()
                        bt_name = match.group("bt_name").strip()
                        entry_point_type = match.group("entry_point_type").strip()
                        key = (bt_id, bt_name, entry_point_type)

                        if key not in unique_bts:
                            unique_bts[key] = {
                                "bt_id": bt_id,
                                "bt_name": bt_name,
                                "entry_point_type": entry_point_type,
                                "file": file_name,
                                "line_num": line_num
                            }
            except Exception:
                continue

        return sorted(
            unique_bts.values(),
            key=lambda item: (item["bt_name"].lower(), item["bt_id"], item["entry_point_type"].lower())
        )

    def extract_registered_backends(log_files: list) -> list:
        """
        Extract unique registered backends from AFastBackendResolver log lines.
        """
        backend_pat = re.compile(
            r"AFastBackendResolver - Caching backend resolution against\s+(?P<backend_name>.+?)\s+for backend ID AExitComponent\{[^}]*backendId=(?P<backend_id>\d+)",
            re.IGNORECASE,
        )

        unique_backends = {}
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        m = backend_pat.search(line)
                        if not m:
                            continue
                        backend_name = m.group("backend_name").strip()
                        backend_id = m.group("backend_id").strip()
                        key = (backend_id, backend_name)
                        if key not in unique_backends:
                            unique_backends[key] = {
                                "backend_id": backend_id,
                                "backend_name": backend_name,
                            }
            except Exception:
                continue

        return sorted(
            unique_backends.values(),
            key=lambda item: (item["backend_name"].lower(), item["backend_id"])
        )

    def extract_registered_service_endpoints(log_files: list) -> list:
        """
        Extract unique service endpoints from ServiceEndPointADDRegistrar lines.
        """
        add_block_pat = re.compile(
            r"ServiceEndPointADDRegistrar\s*-\s*Registered ADDs\s*\[\{(?P<adds>.*)\}\]",
            re.IGNORECASE,
        )
        add_item_pat = re.compile(
            r"(?P<raw_name>[^=]+?)=(?P<sep_id>\d+)",
            re.IGNORECASE,
        )

        unique_service_endpoints = {}

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        block_match = add_block_pat.search(line)
                        if not block_match:
                            continue

                        add_block = block_match.group("adds")
                        for item in add_block.split(","):
                            item = item.strip()
                            if not item:
                                continue

                            item_match = add_item_pat.search(item)
                            if not item_match:
                                continue

                            raw_name = item_match.group("raw_name").strip()
                            sep_id = item_match.group("sep_id").strip()

                            sep_type = "UNKNOWN"
                            sep_name = raw_name
                            if "_" in raw_name:
                                sep_name, sep_type = raw_name.rsplit("_", 1)
                                sep_name = sep_name.strip()
                                sep_type = sep_type.strip().upper()

                            key = (sep_name, sep_type, sep_id)
                            if key not in unique_service_endpoints:
                                unique_service_endpoints[key] = {
                                    "sep_name": sep_name,
                                    "sep_type": sep_type,
                                    "sep_id": sep_id,
                                }
            except Exception:
                continue

        return sorted(
            unique_service_endpoints.values(),
            key=lambda item: (item["sep_name"].lower(), item["sep_type"], item["sep_id"])
        )

    def extract_registered_errors(log_files: list) -> list:
        """
        Extract unique registered error objects from ErrorProcessor lines.
        """
        error_block_pat = re.compile(
            r"ErrorProcessor\s*-\s*Error Objects registered with controller\s*:\s*\{(?P<errors>.*)\}",
            re.IGNORECASE,
        )
        error_item_pat = re.compile(
            r"(?P<error_name>.+?):=(?P<error_id>\d+)",
            re.IGNORECASE,
        )

        unique_registered_errors = {}

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        block_match = error_block_pat.search(line)
                        if not block_match:
                            continue

                        error_block = block_match.group("errors")
                        for item in error_block.split(","):
                            item = item.strip()
                            if not item:
                                continue

                            item_match = error_item_pat.search(item)
                            if not item_match:
                                continue

                            error_name = item_match.group("error_name").strip()
                            error_id = item_match.group("error_id").strip()

                            key = (error_name, error_id)
                            if key not in unique_registered_errors:
                                unique_registered_errors[key] = {
                                    "error_name": error_name,
                                    "error_id": error_id,
                                }
            except Exception:
                continue

        return sorted(
            unique_registered_errors.values(),
            key=lambda item: (item["error_name"].lower(), item["error_id"])
        )

    def extract_node_properties(log_files: list) -> list:
        """
        Extract node property assignments from agent logs.
        Handles four patterns:
          1) Set property <name>=<value> on <class>
          2) Received property update for [<name>], value[<value>]
          3) Applying '<name>', '<value>'
          4) Applying property <name>, val <value>
        Keeps the latest value per property name (by timestamp).
        """
        from datetime import datetime

        # Timestamp pattern: DD Mon YYYY HH:MM:SS,mmm
        ts_pat = re.compile(
            r"\]\s+(\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3})"
        )
        # Logger class name between log level and " - "
        class_pat = re.compile(r"\s+(?:INFO|DEBUG|WARN|ERROR|TRACE)\s+([\w$]+)\s+-")

        # Pattern 1: Set property <name>=<value> on <class>
        p1 = re.compile(r"Set property\s+([\w.\-]+)=(.+?)\s+on\s+(\w+)", re.IGNORECASE)
        # Pattern 2: Received property update for [<name>], value[<value>]
        p2 = re.compile(
            r"Received property update for\s+\[([^\]]+)\],\s*value\[([^\]]*)\]",
            re.IGNORECASE,
        )
        # Pattern 3: Applying '<name>', '<value>'
        p3 = re.compile(r"Applying\s+'([^']+)',\s*'([^']*)'", re.IGNORECASE)
        # Pattern 4: Applying property <name>, val <value>
        p4 = re.compile(r"Applying property\s+([\w.\-]+),\s*val\s+(.*)", re.IGNORECASE)

        TS_FMT = "%d %b %Y %H:%M:%S,%f"
        MIN_TS = datetime.min

        # Keyed by property name → {name, value, source, timestamp_dt, timestamp_str, file, file_name, line_num}
        props: dict = {}

        for log_file in log_files:
            file_name = os.path.basename(log_file)
            relative_path = os.path.relpath(log_file, log_dir)
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Extract timestamp
                        ts_m = ts_pat.search(line)
                        if ts_m:
                            try:
                                ts_dt = datetime.strptime(ts_m.group(1), TS_FMT)
                            except ValueError:
                                ts_dt = MIN_TS
                            ts_str = ts_m.group(1)
                        else:
                            ts_dt = MIN_TS
                            ts_str = ""

                        # Extract logger class
                        cls_m = class_pat.search(line)
                        source = cls_m.group(1) if cls_m else ""

                        prop_name = prop_value = None

                        m1 = p1.search(line)
                        if m1:
                            prop_name = m1.group(1).strip()
                            prop_value = m1.group(2).strip()
                            if not source:
                                source = m1.group(3).strip()
                        elif (m2 := p2.search(line)):
                            prop_name = m2.group(1).strip()
                            prop_value = m2.group(2).strip()
                        elif (m3 := p3.search(line)):
                            prop_name = m3.group(1).strip()
                            prop_value = m3.group(2).strip()
                        elif (m4 := p4.search(line)):
                            prop_name = m4.group(1).strip()
                            prop_value = m4.group(2).strip()

                        if prop_name is None:
                            continue

                        existing = props.get(prop_name)
                        if existing is None or ts_dt >= existing["timestamp_dt"]:
                            props[prop_name] = {
                                "name": prop_name,
                                "value": prop_value,
                                "source": source,
                                "timestamp_dt": ts_dt,
                                "timestamp_str": ts_str,
                                "file": relative_path,
                                "file_name": file_name,
                                "line_num": line_num,
                            }
            except Exception:
                continue

        result_list = sorted(props.values(), key=lambda x: x["name"].lower())
        # Drop the non-serialisable datetime before returning
        for item in result_list:
            item.pop("timestamp_dt", None)
        return result_list

    def extract_failed_service_endpoints(log_files: list) -> dict:
        """
        Extract failed SEP registration warnings:
        1) Nested SEP ignored by interceptor
        2) ADD flagged for blacklisting
        """
        nested_sep_pat = re.compile(
            r"Ignoring nested SEP\s+ServiceEndPointNameAndType\{\s*"
            r"serviceEndPointName='(?P<sep_name>[^']+)'\s*,\s*"
            r"serviceEndPointType='(?P<sep_type>[^']+)'",
            re.IGNORECASE,
        )

        blacklisted_sep_pat = re.compile(
            r"ServiceEndPointADDRegistrar\s*-\s*ADD\s+"
            r"(?P<raw_sep>[^\s]+)\s+has been flagged for blacklisting",
            re.IGNORECASE,
        )

        known_sep_types = [
            "WEB_SERVICE",
            "SERVLET",
            "POJO",
            "ASYNC",
            "JMS",
            "RABBITMQ",
            "KAFKA",
        ]

        nested_unique = {}
        blacklisted_unique = {}

        for log_file in log_files:
            file_name = os.path.basename(log_file)
            relative_path = os.path.relpath(log_file, log_dir)
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        nested_match = nested_sep_pat.search(line)
                        if nested_match:
                            sep_name = nested_match.group("sep_name").strip()
                            sep_type = nested_match.group("sep_type").strip().upper()
                            key = (sep_name, sep_type)
                            if key not in nested_unique:
                                nested_unique[key] = {
                                    "sep_name": sep_name,
                                    "sep_type": sep_type,
                                    "file": relative_path,
                                    "file_name": file_name,
                                    "line_num": line_num,
                                    "line": line.strip(),
                                }

                        blacklisted_match = blacklisted_sep_pat.search(line)
                        if blacklisted_match:
                            raw_sep = blacklisted_match.group("raw_sep").strip()
                            sep_name = raw_sep
                            sep_type = "UNKNOWN"

                            upper_raw_sep = raw_sep.upper()
                            for candidate_type in known_sep_types:
                                suffix = f"_{candidate_type}"
                                if upper_raw_sep.endswith(suffix):
                                    sep_name = raw_sep[: -len(suffix)].strip()
                                    sep_type = candidate_type
                                    break

                            if sep_type == "UNKNOWN" and "_" in raw_sep:
                                sep_name, sep_type = raw_sep.rsplit("_", 1)
                                sep_name = sep_name.strip()
                                sep_type = sep_type.strip().upper()

                            key = (sep_name, sep_type)
                            if key not in blacklisted_unique:
                                blacklisted_unique[key] = {
                                    "sep_name": sep_name,
                                    "sep_type": sep_type,
                                    "file": relative_path,
                                    "file_name": file_name,
                                    "line_num": line_num,
                                    "line": line.strip(),
                                }
            except Exception:
                continue

        nested_list = sorted(
            nested_unique.values(),
            key=lambda x: (x["sep_name"].lower(), x["sep_type"]),
        )
        blacklisted_list = sorted(
            blacklisted_unique.values(),
            key=lambda x: (x["sep_name"].lower(), x["sep_type"]),
        )

        return {
            "nested_seps": nested_list,
            "blacklisted_seps": blacklisted_list,
        }

    def extract_logger_issues(log_files: list) -> list:
        """
        Extract the logger class name from every ERROR / WARN line across all
        agent log files.  For each unique logger, keep the single latest
        occurrence (by line timestamp, then file mtime, then line number) so
        callers can show a representative example from the newest data.

        Returns a list of dicts sorted by descending occurrence count:
          {
            "logger"       : str,   # e.g. "MetricSender"
            "level"        : str,   # "ERROR" | "WARN"
            "latest_line"  : str,   # full raw log line
            "timestamp"    : str,   # extracted timestamp string  (may be "")
            "file_name"    : str,   # basename of the source file
            "occurrences"  : int,
          }
        """
        # Matches: [thread] DD Mon YYYY HH:MM:SS,mmm  LEVEL  LoggerClass -
        log_pat = re.compile(
            r"^\[[^\]]+\]\s+"
            r"(?P<ts>\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2},\d{3})\s+"
            r"(?P<level>ERROR|WARN)\s+"
            r"(?P<logger>[\w$]+)\s+-",
            re.IGNORECASE,
        )
        ts_fmt = "%d %b %Y %H:%M:%S,%f"
        min_dt = datetime.min

        # key = (logger, level) → best candidate
        best: dict = {}

        for log_file in log_files:
            try:
                file_mtime = os.path.getmtime(log_file)
            except OSError:
                file_mtime = float("-inf")
            file_name = os.path.basename(log_file)
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        m = log_pat.match(line)
                        if not m:
                            continue
                        logger = m.group("logger")
                        level  = m.group("level").upper()
                        ts_str = m.group("ts")
                        try:
                            ts_dt = datetime.strptime(ts_str, ts_fmt)
                        except ValueError:
                            ts_dt = min_dt

                        key = (logger, level)
                        candidate_key = (ts_dt, file_mtime, line_num)
                        entry = best.get(key)
                        if entry is None:
                            best[key] = {
                                "logger":       logger,
                                "level":        level,
                                "latest_line":  line.rstrip("\n"),
                                "timestamp":    ts_str,
                                "file_name":    file_name,
                                "occurrences":  1,
                                "_sort_key":    candidate_key,
                            }
                        else:
                            entry["occurrences"] += 1
                            if candidate_key >= entry["_sort_key"]:
                                entry["_sort_key"]   = candidate_key
                                entry["latest_line"] = line.rstrip("\n")
                                entry["timestamp"]   = ts_str
                                entry["file_name"]   = file_name
            except Exception:
                continue

        result_list = sorted(
            best.values(),
            key=lambda x: x["occurrences"],
            reverse=True,
        )
        for item in result_list:
            item.pop("_sort_key", None)
        return result_list

    def extract_latest_jvm_pid(log_files: list):
        """
        Extract JVM PID from the latest PID log event.
        Ordering preference:
        1) Newest line timestamp in log content
        2) Newest file modified time
        3) Latest line number within the file
        """
        pid_pat = re.compile(r"JVM PID:\s*(\d+)", re.IGNORECASE)

        best_pid = None
        best_key = (min_ts, float("-inf"), -1)

        for log_file in log_files:
            try:
                file_mtime = os.path.getmtime(log_file)
            except OSError:
                file_mtime = float("-inf")

            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        pid_match = pid_pat.search(line)
                        if not pid_match:
                            continue

                        line_ts = parse_line_timestamp(line)
                        candidate_key = (line_ts, file_mtime, line_num)
                        if candidate_key >= best_key:
                            best_key = candidate_key
                            best_pid = pid_match.group(1)
            except Exception:
                continue

        return best_pid

    # Initialize all fields
    appagent_dir = None
    controller_host = None
    controller_port = None
    controller_ssl = None
    application_name = None
    tier_name = None
    node_name = None
    registration_host_name = None
    registration_node_id = None
    registration_component_id = None
    registration_application_id = None
    controller_version = None
    java_home = None
    java_vm_vendor = None
    java_vm_name = None
    java_version = None
    java_agent_version = None
    os_name = None
    jvm_args = None
    jvm_runtime_name = None
    jvm_pid = None

    # Patterns
    appagent_pat = re.compile(r"AppAgent directory\s*\[(.*?)\]", re.IGNORECASE)
    controller_info_pat = re.compile(r"Configuration Channel is using ControllerInfo::\s*host:\[(.*?)\]\s+port:\[(.*?)\]\s+sslEnabled:\[(.*?)\]", re.IGNORECASE)
    registration_info_pat = re.compile(
        r"Sending Registration request with:\s*Application Name\s*\[(.*?)\],\s*"
        r"Tier Name\s*\[(.*?)\],\s*"
        r"Node Name\s*\[(.*?)\],\s*"
        r"Host Name\s*\[(.*?)\]",
        re.IGNORECASE,
    )
    registration_ids_pat = re.compile(
        r"Registration information received\s+Node ID\[(?P<node_id>\d+)\]\s+"
        r"Component ID\[(?P<component_id>\d+)\]\s+"
        r"Application ID\s*\[(?P<application_id>\d+)\]",
        re.IGNORECASE,
    )
    controller_version_pat = re.compile(r"Controller version\s*\[(?P<controller_version>[^\]]+)\]", re.IGNORECASE)
    jvm_runtime_pat = re.compile(r"JVM Runtime:", re.IGNORECASE)
    os_runtime_pat = re.compile(r"OS Runtime:", re.IGNORECASE)
    jvm_args_pat = re.compile(r"JVM Args\s*:\s*(.*)", re.IGNORECASE)
    jvm_runtime_name_pat = re.compile(r"JVM Runtime Name:\s*(.*)", re.IGNORECASE)
    java_agent_version_pat = re.compile(r"Using Java Agent Version\s*\[(.+)\]\s*$", re.IGNORECASE)
    java_agent_version_fallback_pat = re.compile(r"Using Java Agent Version\s*:?\s*(.+)$", re.IGNORECASE)

    # Patterns for multi-line sections
    java_home_pat = re.compile(r"java\.home=(.+)")
    java_vm_vendor_pat = re.compile(r"java\.vm\.vendor=(.+)")
    java_vm_name_pat = re.compile(r"java\.vm\.name=(.+)")
    java_version_pat = re.compile(r"java\.version=(.+)")
    os_name_pat = re.compile(r"os\.name=(.+)")

    # Scan agent logs (agent.log and agent.*.log)
    log_files = [
        os.path.join(log_dir, fname)
        for fname in os.listdir(log_dir)
        if (
            fnmatch.fnmatch(fname, 'agent.log')
            or fnmatch.fnmatch(fname, 'agent.*.log')
        )
    ]
    if not log_files:
        return {"error": "No agent log file found in directory."}

    # Sort by last modified time to favor latest logs first
    log_files.sort(key=lambda p: (os.path.getmtime(p), p))

    error_summary = extract_error_summaries(log_files)
    warn_summary = extract_warn_summaries(log_files)
    registered_business_transactions = extract_registered_business_transactions(log_files)
    registered_backends = extract_registered_backends(log_files)
    registered_service_endpoints = extract_registered_service_endpoints(log_files)
    registered_errors = extract_registered_errors(log_files)
    node_properties = extract_node_properties(log_files)
    failed_seps = extract_failed_service_endpoints(log_files)
    jvm_pid = extract_latest_jvm_pid(log_files)
    logger_issues = extract_logger_issues(log_files)
    agent_checkpoints = extract_agent_checkpoints(log_files)

    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i]

                # Check for AppAgent directory
                if appagent_dir is None:
                    m = appagent_pat.search(line)
                    if m:
                        appagent_dir = m.group(1)

                # Check for ControllerInfo
                if controller_host is None or controller_port is None or controller_ssl is None:
                    m = controller_info_pat.search(line)
                    if m:
                        controller_host = m.group(1)
                        controller_port = m.group(2)
                        controller_ssl = m.group(3)

                # Check for registration details (Application/Tier/Node/Host names)
                if application_name is None or tier_name is None or node_name is None or registration_host_name is None:
                    m = registration_info_pat.search(line)
                    if m:
                        application_name = m.group(1).strip()
                        tier_name = m.group(2).strip()
                        node_name = m.group(3).strip()
                        registration_host_name = m.group(4).strip()

                # Check for registration IDs (Node/Component/Application IDs)
                if (
                    registration_node_id is None
                    or registration_component_id is None
                    or registration_application_id is None
                ):
                    m = registration_ids_pat.search(line)
                    if m:
                        registration_node_id = m.group("node_id").strip()
                        registration_component_id = m.group("component_id").strip()
                        registration_application_id = m.group("application_id").strip()

                # Check for controller version
                if controller_version is None:
                    m = controller_version_pat.search(line)
                    if m:
                        controller_version = m.group("controller_version").strip()

                # Check for JVM Runtime section
                if jvm_runtime_pat.search(line):
                    i += 1
                    while i < len(lines):
                        prop_line = lines[i].strip()
                        if not prop_line or prop_line.startswith("["):  # End of section
                            break
                        if java_home is None:
                            m = java_home_pat.search(prop_line)
                            if m:
                                java_home = m.group(1)
                        if java_vm_vendor is None:
                            m = java_vm_vendor_pat.search(prop_line)
                            if m:
                                java_vm_vendor = m.group(1)
                        if java_vm_name is None:
                            m = java_vm_name_pat.search(prop_line)
                            if m:
                                java_vm_name = m.group(1)
                        if java_version is None:
                            m = java_version_pat.search(prop_line)
                            if m:
                                java_version = m.group(1)
                        i += 1
                    continue

                # Check for OS Runtime section
                if os_runtime_pat.search(line):
                    i += 1
                    while i < len(lines):
                        prop_line = lines[i].strip()
                        if not prop_line or prop_line.startswith("["):  # End of section
                            break
                        if os_name is None:
                            m = os_name_pat.search(prop_line)
                            if m:
                                os_name = m.group(1)
                        i += 1
                    continue

                # Check for JVM Args
                if jvm_args is None:
                    m = jvm_args_pat.search(line)
                    if m:
                        jvm_args = m.group(1).strip()

                # Check for Java Agent Version
                if java_agent_version is None:
                    m = java_agent_version_pat.search(line)
                    if m:
                        java_agent_version = m.group(1).strip()
                    else:
                        m = java_agent_version_fallback_pat.search(line)
                        if m:
                            java_agent_version = m.group(1).strip().strip('[]')

                # Check for JVM Runtime Name
                if jvm_runtime_name is None:
                    m = jvm_runtime_name_pat.search(line)
                    if m:
                        jvm_runtime_name = m.group(1).strip()

                i += 1

        # If we found all required fields, stop searching
        if all([
            appagent_dir,
            controller_host,
            controller_port,
            controller_ssl,
            application_name,
            tier_name,
            node_name,
            registration_host_name,
            java_home,
            java_vm_vendor,
            java_vm_name,
            java_version,
            java_agent_version,
            os_name,
            jvm_args,
            jvm_runtime_name,
            jvm_pid,
        ]):
            break

    return {
        "appagent_dir": appagent_dir,
        "controller_host": controller_host,
        "controller_port": controller_port,
        "controller_ssl_enabled": controller_ssl,
        "controller_version": controller_version,
        "application_name": application_name,
        "tier_name": tier_name,
        "node_name": node_name,
        "registration_host_name": registration_host_name,
        "registration_node_id": registration_node_id,
        "registration_component_id": registration_component_id,
        "registration_application_id": registration_application_id,
        "java_home": java_home,
        "java_vm_vendor": java_vm_vendor,
        "java_vm_name": java_vm_name,
        "java_version": java_version,
        "java_agent_version": java_agent_version,
        "os_name": os_name,
        "jvm_args": jvm_args,
        "jvm_runtime_name": jvm_runtime_name,
        "jvm_pid": jvm_pid,
        "error_summary": error_summary,
        "warn_summary": warn_summary,
        "registered_business_transactions": registered_business_transactions,
        "registered_backends": registered_backends,
        "registered_service_endpoints": registered_service_endpoints,
        "registered_errors": registered_errors,
        "node_properties": node_properties,
        "failed_seps": failed_seps,
        "agent_checkpoints": agent_checkpoints,
        "logger_issues": logger_issues,
    }