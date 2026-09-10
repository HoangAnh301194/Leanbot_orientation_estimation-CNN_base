from __future__ import annotations

import argparse
import asyncio

from logs import (
    logs_init,
    logs_shutdown,
    set_log_file,
    log,
)

from LeanbotController import (
    LeanbotController,
)


# =========================================================================
# CLI
# =========================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "leanbot service.\n\n"
            "This program initializes a leanbot, connects it to "
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--leanbot",
        type=int,
        required=True,
        help=(
            "leanbot ID.\n\n"
            "Example:\n"
            "  --leanbot 123456"
        ),
    )

    parser.add_argument(
        "--pathlog",
        type=str,
        default=None,
        help=(
            "Path to the log file.\n"
            "If omitted, logs are printed to stdout only.\n\n"
            "Example:\n"
            "  --pathlog ./logs/remoteleanbot.log"
        ),
    )

    return parser.parse_args()


# =========================================================================
# MAIN
# =========================================================================


async def main() -> None:
    args = parse_args()

    # ---------------------------------------------------------------------
    # Initialize logger
    # ---------------------------------------------------------------------

    await logs_init()

    if args.pathlog:
        set_log_file(args.pathlog)

    leanbot: leanbot | None = None

    try:
        log(
            "SYS",
            "=== Starting leanbot ===",
        )

        log(
            "SYS",
            f"leanbot ID: {args.leanbot}",
        )

        if args.pathlog:
            log(
                "SYS",
                f"Log file: {args.pathlog}",
            )
        else:
            log(
                "SYS",
                "Log file: disabled",
            )

        # -----------------------------------------------------------------
        # Create leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "Initializing BLE Leanbot...",
        )
        leanbot = LeanbotController(args.leanbot)

        # -----------------------------------------------------------------
        # Initialize BLE Leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "Connect leanbot...",
        )
        
        await leanbot.find()
        await leanbot.connect()

        log(
            "SYS",
            "Press Ctrl+C to stop",
        )

        await leanbot.manualControlLeanbotRC()

    except asyncio.CancelledError:
        log(
            "SYS",
            "leanbot task cancelled",
        )

    except KeyboardInterrupt:
        log(
            "SYS",
            "Ctrl+C received. Stopping...",
        )

    except Exception as error:
        log(
            "SYS",
            f"Unexpected error: {error}",
        )

    finally:
        # -----------------------------------------------------------------
        # Cleanup leanbot
        # -----------------------------------------------------------------

        log(
            "SYS",
            "=== Shutting down leanbot ===",
        )

        log(
            "SYS",
            "=== leanbot stopped ===",
        )

        await logs_shutdown()


# =========================================================================
# ENTRY POINT
# =========================================================================


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass