import argparse
from . import cleanup_assignments

def parse_args(args=None):  # type: (Optional[List[str]]) -> argparse.Namespace
    parser = argparse.ArgumentParser(description="Import media data for given product ids")
    parser.add_argument(
        "--entry-uuid",
        help=(
            "The entryUUID of the object which assignments should be lifted if possible."
        ),
    )
    return parser.parse_args(args)


def main():
    args = parse_args()
    cleanup_assignments(args.entry_uuid)


if __name__ == "__main__":
    main()
