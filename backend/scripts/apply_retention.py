"""Apply or preview the approved MedFlow retention policy."""

import argparse
import json

from app.core.database import SessionLocal
from app.services.retention import apply_retention


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit changes; default is rollback")
    parser.add_argument("--clinical-retention-days", type=int, default=2557)
    parser.add_argument("--refresh-history-days", type=int, default=90)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = apply_retention(
            db,
            clinical_retention_days=args.clinical_retention_days,
            refresh_history_days=args.refresh_history_days,
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps({"mode": "apply" if args.apply else "dry-run", **result.to_dict()}))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
