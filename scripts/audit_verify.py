import argparse
import json
from common.audit_chain import verify_range


def main():
    ap = argparse.ArgumentParser(description="Verify tamper-evident audit chain")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (start)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (end, optional)")
    args = ap.parse_args()
    rep = verify_range(args.date, args.end)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
