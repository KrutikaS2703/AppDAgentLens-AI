#!/usr/bin/env python3
import argparse
from core.bct.scanner import run_bct_analysis


def main():
    parser = argparse.ArgumentParser(
        description="AppDynamics BCT Log Analyzer"
    )
    parser.add_argument("path", help="Path to BCT log directory")
    parser.add_argument("--top", type=int, default=0)

    args = parser.parse_args()

    result = run_bct_analysis(args.path)

    print(f"\nTotal matched classes: {result['matched_count']}")
    print(f"Total applied interceptor classes: {result['applied_count']}")
    print(f"Total unique interceptors: {result['unique_interceptors']}")
    print(f"Total classes with no interceptors: {result['no_interceptor_count']}")

    print("\nTop interceptors:")
    counts = result["interceptor_counts"]
    items = counts.most_common(args.top) if args.top else counts.most_common()

    for interceptor, count in items:
        print(f"{interceptor}: {count}")

    print("\nFinal exclusion suggestions:\n")
    for pkg, count in sorted(
        result["exclusion_suggestions"].items(),
        key=lambda x: -x[1]
    ):
        print(f"{pkg} → {count} classes")

    print("\n=== BCI Exclude Configuration ===")
    for line in result["bci_exclude_config"]:
        print(line)


if __name__ == "__main__":
    main()
