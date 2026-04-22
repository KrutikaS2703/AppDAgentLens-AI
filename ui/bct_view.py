import streamlit as st
import pandas as pd

from ai.rules import assess_risk
from ai.analyzer import detect_frameworks_used, explain_package

from core.bct.scanner import run_bct_analysis


def _is_appd_class(class_name: str) -> bool:
    normalized = (class_name or "").strip().lower().replace(".", "/")
    return normalized.startswith("com/appdynamics/")

def render_bct():
    st.title("🔍 BCT logs Analysis")
    if not st.session_state.scan_done:
        st.info("👈 Click **Scan JavaAgent Logs** to start analysis")
    if not st.session_state.scan_done:
        st.info("Run scan from sidebar")
        return

    result = st.session_state.bct_result
    if not result:
        st.warning("No BCT data found")
        return

    # PURE DISPLAY
    matched = result["matched_classes"]
    applied = result["applied_classes"]
    applied_by_interceptor = result.get("applied_by_interceptor", {})
    interceptor_counts = result["interceptor_counts"]
    no_interceptor_classes = result["no_interceptor_classes"]
    excludable_pkgs = result["excludable_packages"]

    #st.metric("Applied Classes", len(applied))



    # =============================
    # Tabs
    # =============================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "📦 All Scanned Classes",
        "🧩 Applied Interceptors Classes",
        "🔢 Interceptor Counts",
        "⚠️ Method Excluded Warnings"
    ])

    # ---------- TAB 1 ----------
    with tab1:
        if not matched:
            st.info("👈 Enter log directory and click **Scan Logs**")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Scanned Classes", len(matched))
            col2.metric("Interceptor Applied Classes", len(applied))
            col3.metric("Unique Interceptors", len(interceptor_counts))

            st.divider()

            st.subheader("🚫 Classes Without Any Interceptors")
            ni_search_col, ni_toggle_col = st.columns([4, 1])
            with ni_search_col:
                ni_search = st.text_input(
                    "🔍 Search classes without interceptors",
                    placeholder="Filter by class name...",
                    key="ni_search",
                )
            with ni_toggle_col:
                show_appd_ni = st.toggle(
                    "Show AppDynamics classes",
                    value=False,
                    key="show_appd_ni",
                    help="Enable to include AppDynamics internal classes in this table.",
                )
            ni_base = no_interceptor_classes if show_appd_ni else [
                c for c in no_interceptor_classes if not _is_appd_class(c)
            ]
            ni_filtered = [c for c in ni_base if ni_search.lower() in c.lower()] if ni_search else ni_base
            with st.expander("📋 Classes Without Interceptors Table", expanded=True):
                st.caption(f"Showing {len(ni_filtered)} of {len(ni_base)}")
                st.dataframe(
                    pd.DataFrame(ni_filtered, columns=["Class"]),
                    width='stretch',
                )

            st.divider()

            st.subheader("🚫 BCI Excludable Packages")

            pkg_rows = []
            for pkg, count in excludable_pkgs.items():
                risk = assess_risk(pkg)
                pkg_rows.append((pkg, count, risk))

            df_pkg = pd.DataFrame(
                pkg_rows,
                columns=["Package", "Classes Excluded", "Risk"]
            )

            pkg_search = st.text_input("🔍 Search packages", placeholder="Filter by package name or risk...", key="pkg_search")
            df_pkg_display = df_pkg[df_pkg.apply(lambda r: pkg_search.lower() in r["Package"].lower() or pkg_search.lower() in r["Risk"].lower(), axis=1)] if pkg_search else df_pkg
            with st.expander("📋 Excludable Packages Table", expanded=True):
                st.caption(f"Showing {len(df_pkg_display)} of {len(df_pkg)}")
                st.dataframe(df_pkg_display, width='stretch')
            
            st.divider()

            #-------------BCI Exclude Configuration-------------

            st.subheader("📋 BCI Exclude Configuration")

            bci_text = "\n".join(
                f'<custom-exclude filter-type="STARTSWITH" filter-value="{pkg}"/>'
                for pkg in df_pkg["Package"]
            )

            st.text_area(
                "Copy BCI exclude XML",
                bci_text,
                height=200
            )

            st.download_button(
                "⬇️ Download BCI Exclude XML",
                data=bci_text,
                file_name="bci_exclude_packages.xml"
            )

            #-------------AI Suggestion-------------
            
            st.subheader("🤖 AI Suggestion")
            if df_pkg.empty:
                st.info("No excludable packages found for AI explanation.")
            else:
                selected_pkg = st.selectbox("Select a package", df_pkg["Package"].tolist())

                if selected_pkg:
                    row = df_pkg[df_pkg["Package"] == selected_pkg].iloc[0]
                    with st.spinner("Asking AI..."):
                        ai = explain_package(
                            selected_pkg,
                            row["Classes Excluded"],
                            row["Risk"]
                        )

                    st.markdown(f"**Risk:** `{ai.get('risk', 'Unknown')}`")
                    st.markdown(f"**Why safe:** {ai.get('explanation', 'No explanation available')}")
                    st.markdown(f"**Impact:** {ai.get('impact', 'No impact analysis available')}")

    # ---------- TAB 2 ----------
    with tab2:
        matched_search_col, matched_toggle_col = st.columns([4, 1])
        with matched_search_col:
            matched_search = st.text_input(
                "🔍 Search matched classes",
                placeholder="Filter by class name...",
                key="matched_search",
            )
        with matched_toggle_col:
            show_appd_matched = st.toggle(
                "Show Appdynamics classes",
                value=False,
                key="show_appd_matched",
                help="Enable to include AppDynamics internal classes in this table.",
            )
        matched_list = sorted(set(matched))
        matched_base = matched_list if show_appd_matched else [
            c for c in matched_list if not _is_appd_class(c)
        ]

        
        matched_filtered = [c for c in matched_base if matched_search.lower() in c.lower()] if matched_search else matched_base
        with st.expander("📋 All Scanned Classes Table", expanded=True):
            st.caption(f"Showing {len(matched_filtered)} of {len(matched_base)}")
            st.dataframe(pd.DataFrame(matched_filtered, columns=["Class"]), width='stretch')

        st.divider()
        st.subheader("🤖 AI Suggestion: Frameworks Used")
        frameworks_used = detect_frameworks_used(matched_base)
        if frameworks_used:
            st.markdown(
                "**Detected frameworks:** "
                + ", ".join(item["framework"] for item in frameworks_used)
            )
            framework_df = pd.DataFrame([
                {
                    "Framework": item["framework"],
                    "Matched Classes": item["class_count"],
                    "AppD Support": item.get("support_summary", ""),
                    "Matching Package Prefixes": ", ".join(item["matching_prefixes"][:4]),
                }
                for item in frameworks_used
            ])
            with st.expander("📋 Detected Frameworks Table", expanded=True):
                st.dataframe(framework_df, width='stretch', height=260)
        else:
            st.caption("No common Java frameworks were identified from the scanned class package prefixes.")


    # ---------- TAB 3 ----------
    with tab3:
        applied_search = st.text_input("🔍 Search applied classes", placeholder="Filter by class name...", key="applied_search")
        applied_list = sorted(set(applied))
        applied_filtered = [c for c in applied_list if applied_search.lower() in c.lower()] if applied_search else applied_list
        with st.expander("📋 Applied Classes Table", expanded=True):
            st.caption(f"Showing {len(applied_filtered)} of {len(applied_list)}")
            st.dataframe(pd.DataFrame(applied_filtered, columns=["Class"]), width='stretch')

        st.divider()

        st.subheader("🔗 Classes by Interceptor")
        interceptor_options = [
            interceptor for interceptor in interceptor_counts.keys()
            if interceptor in applied_by_interceptor
        ]

        if not interceptor_options:
            st.info("No applied interceptor details found")
        else:
            selected_applied_interceptor = st.selectbox(
                "Select interceptor to view applied classes and methods",
                interceptor_options,
                key="applied_interceptor_select",
            )

            applied_details = applied_by_interceptor.get(selected_applied_interceptor, {})
            applied_rows = [
                {
                    "Class": class_name,
                    "Methods": ", ".join(methods) if methods else "",
                }
                for class_name, methods in applied_details.items()
            ]
            df_applied_details = pd.DataFrame(applied_rows)

            ad_search = st.text_input(
                "🔍 Search classes or methods for selected interceptor",
                placeholder="Filter by class or method...",
                key="applied_interceptor_detail_search",
            )
            if ad_search and not df_applied_details.empty:
                df_applied_details = df_applied_details[
                    df_applied_details.apply(
                        lambda row: ad_search.lower() in row["Class"].lower()
                        or ad_search.lower() in row["Methods"].lower(),
                        axis=1,
                    )
                ]

            with st.expander("📋 Classes by Selected Interceptor Table", expanded=True):
                st.caption(f"Showing {len(df_applied_details)} of {len(applied_rows)}")
                st.dataframe(df_applied_details, width='stretch')

    # ---------- TAB 4 ----------
    with tab4:
        df = pd.DataFrame(
            interceptor_counts.items(),
            columns=["Interceptor", "Count"]
        ).sort_values("Count", ascending=False)

        ic_search = st.text_input("🔍 Search interceptors", placeholder="Filter by interceptor name...", key="ic_search")
        df_ic = df[df["Interceptor"].str.contains(ic_search, case=False, na=False)] if ic_search else df
        with st.expander("📋 Interceptor Counts Table", expanded=True):
            st.caption(f"Showing {len(df_ic)} of {len(df)}")
            st.dataframe(df_ic, width='stretch')
        st.bar_chart(df_ic.set_index("Interceptor")["Count"])

    # ---------- TAB 5 ----------
    with tab5:
        excluded_methods = result.get("excluded_methods", [])
        unique_excluded_classes = result.get("unique_excluded_classes", {})
        excluded_methods_objects = result.get("excluded_methods_objects", [])
        excluded_by_interceptor = result.get("excluded_by_interceptor", {})
        
        if not excluded_methods:
            st.info("✅ No method excluded warnings found")
        else:
            st.metric("Total Excluded Methods", result.get("excluded_count", 0))
            st.metric("Unique Problematic Classes", len(unique_excluded_classes))
            
            with st.expander("📋 Unique Problematic Classes", expanded=True):
                unique_class_rows = []
                for class_name, details in sorted(unique_excluded_classes.items()):
                    unique_class_rows.append({
                        "Class": class_name,
                        "Interceptors": ", ".join(details["interceptors"]),
                        "Transformation Limits": ", ".join(str(x) for x in details["transformation_limits"])
                    })
                df_unique = pd.DataFrame(unique_class_rows)
                uc_search = st.text_input("🔍 Search problematic classes", placeholder="Filter by class or interceptor...", key="uc_search")
                if uc_search and not df_unique.empty:
                    df_unique = df_unique[df_unique.apply(lambda r: uc_search.lower() in r["Class"].lower() or uc_search.lower() in r["Interceptors"].lower(), axis=1)]
                st.caption(f"Showing {len(df_unique)} results")
                st.dataframe(df_unique, width='stretch')

            with st.expander("🔗 Classes by Interceptor", expanded=False):
                selected_interceptor = st.selectbox(
                    "Select interceptor to view affected classes",
                    list(excluded_by_interceptor.keys()) if excluded_by_interceptor else []
                )

                if selected_interceptor and excluded_by_interceptor:
                    details = excluded_by_interceptor[selected_interceptor]
                    # Get unique class names for this interceptor
                    unique_classes = list(set([item["class"] for item in details]))
                    df_unique_classes = pd.DataFrame(
                        {"Class": sorted(unique_classes)}
                    )
                    st.dataframe(df_unique_classes, width='stretch')

            with st.expander("🔗 Excluded Methods by Interceptor", expanded=False):
                if excluded_by_interceptor:
                    interceptor_counts_exc = {
                        k: len(v) for k, v in excluded_by_interceptor.items()
                    }
                    df_int = pd.DataFrame(
                        interceptor_counts_exc.items(),
                        columns=["Interceptor", "Count"]
                    ).sort_values("Count", ascending=False)

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.dataframe(df_int, width='stretch')
                    with col2:
                        st.bar_chart(df_int.set_index("Interceptor")["Count"])
                else:
                    st.info("No excluded interceptor data found")

            with st.expander("📦 Excluded Methods by Package Prefix", expanded=False):
                excluded_by_prefix = result.get("excluded_by_prefix", {})

                if excluded_by_prefix:
                    prefix_counts = {
                        k: len(v) for k, v in excluded_by_prefix.items()
                    }
                    df_prefix = pd.DataFrame(
                        prefix_counts.items(),
                        columns=["Prefix", "Count"]
                    ).sort_values("Count", ascending=False)

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.dataframe(df_prefix, width='stretch')
                    with col2:
                        st.bar_chart(df_prefix.set_index("Prefix")["Count"])
                else:
                    st.info("No excluded package prefix data found")

            with st.expander("📊 Excluded Methods by Transformation Limit", expanded=False):
                excluded_by_limit = result.get("excluded_by_limit", {})

                if excluded_by_limit:
                    limit_counts = {
                        str(k): len(v) for k, v in excluded_by_limit.items()
                    }
                    df_limit = pd.DataFrame(
                        limit_counts.items(),
                        columns=["Limit", "Count"]
                    ).sort_values("Count", ascending=False)

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.dataframe(df_limit, width='stretch')
                    with col2:
                        st.bar_chart(df_limit.set_index("Limit")["Count"])
                else:
                    st.info("No excluded transformation limit data found")
            

