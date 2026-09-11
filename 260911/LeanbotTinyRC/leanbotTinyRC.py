import asyncio
import msvcrt

from logs import log


def calc_run_lr(
    velocity: int,
    speed_l: int,
    speed_r: int,
) -> tuple[int, int]:

    left = velocity * speed_l // 4
    right = velocity * speed_r // 4

    return left, right


async def run_lr(
    controller,
    velocity: int,
    speed_l: int,
    speed_r: int,
) -> None:

    left, right = calc_run_lr(
        velocity,
        speed_l,
        speed_r,
    )

    command = f"r/{left}/{right}\n"

    log("TX", command.rstrip())

    await controller.send(
        command,
        response=False,
    )


def get_config(controller) -> dict:
    try:
        return controller.config[
            "LeanbotController"
        ][
            "LeanbotTinyRC"
        ][
            "ManualControl"
        ]

    except KeyError as error:
        raise RuntimeError(
            "LeanbotTinyRC.ManualControl "
            "configuration is missing"
        ) from error


async def manual_control(controller) -> None:

    config = get_config(controller)

    velocity = int(
        config["Velocity"]
    )

    keymap = config["KeyMap"]

    end_key = str(
        config["ControlKey"]["End"]
    ).lower()

    if not controller.is_connected():
        raise RuntimeError(
            "Cannot start manual control: "
            "Leanbot is not connected"
        )

    log(
        "RC",
        f"Leanbot Tiny RC manual control started. "
        f"End RC: {end_key!r}",
    )

    try:

        while controller.is_connected():

            RC = await asyncio.to_thread(
                msvcrt.getwch
            )

            RC = RC.lower()

            if RC == end_key:
                log(
                    "RC",
                    f"End RC {end_key!r} pressed",
                )
                break

            if RC not in keymap:
                continue

            command_config = keymap[RC]

            command_name = str(
                command_config["name"]
            )

            speed_l = int(
                command_config["speed_l"]
            )

            speed_r = int(
                command_config["speed_r"]
            )

            await run_lr(
                controller,
                velocity,
                speed_l,
                speed_r,
            )

            left, right = calc_run_lr(
                velocity,
                speed_l,
                speed_r,
            )

            log('RC KEY', f"[{RC.upper()}] {command_name:15} -> RunLR({left}, {right})")
            # print(
            #     f"[{RC.upper()}] "
            #     f"{command_name:15} "
            #     f"-> RunLR({left}, {right})",
            #     flush=True,
            # )

    finally:

        if controller.is_connected():

            try:
                await run_lr(
                    controller,
                    velocity,
                    0,
                    0,
                )

            except Exception as error:
                log(
                    "RC",
                    f"Failed to stop Leanbot: "
                    f"{type(error).__name__}: {error}",
                )

    log(
        "RC",
        "Leanbot Tiny RC manual control ended",
    )