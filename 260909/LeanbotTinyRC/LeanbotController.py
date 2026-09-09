import asyncio
import time

from pathlib import Path
import shutil
from typing import Any, Callable, Optional
import inspect

from leanbot_ble import LeanbotBLE
from logs import log

import leanbotTinyRC

import traceback
import logging

#####################################################################
# Load config 
#####################################################################

import yaml

def load_config(config_file: str | Path) -> dict:
    """
    Load the YAML configuration file.
    """

    config_path = Path(config_file).resolve()

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    config["_config_dir"] = config_path.parent

    return config

#####################################################################

class LeanbotController:
    """
    Thin wrapper around LeanbotBLE.

    Responsibilities:
        - Own one LeanbotBLE instance
        - Expose upload / bootloader operations
        - Expose firmware pipe operations
        - Expose upload progress
        - Provide a place for higher-level serial commands
    """

    def __init__(
        self,
        leanbotid: int,
    ):
        self.config = load_config("config.yaml")
        log("Controller",f"config.yaml: \n {self.config}")

        self.leanbotid = f"Leanbot {leanbotid} BLE"

        self.serialMessageQueue: asyncio.Queue[str] = asyncio.Queue()
        self.serialLineBuffer: str = ""
        self.serialBufferOpen:bool = True

        self.leanbot = LeanbotBLE(
            notify_callback=self.serial_notification_handler,
            name=self.leanbotid,
        )

        self.is_uploading = False
        self._started = False

    # ======================================================================
    # Start
    # ======================================================================

    async def start(self):
        try:
            config_dir = self.config["_config_dir"]

            code_dir = (
                config_dir /
                self.config["LeanbotController"]["LeanbotCodeDir"]
            ).resolve()

            hex_dir = (
                config_dir /
                self.config["LeanbotController"]["LeanbotHexCompiledDir"]
            ).resolve()


            log('Controller', 'Start Compile all controller code...')
            try:
                t1 = time.perf_counter()
                self.hex_map = await compile_directory(
                    source_dir=code_dir,
                    output_dir=hex_dir,
                    compile_server=self.config["LeanbotCompiler"]["Server"],
                )
            finally:
                t2 = time.perf_counter()
                log('Controller', f'Compile Done in {t2 - t1:.3f}s')

            # await self.find()
            # await self.connect()

            self._started = True

        except Exception as error:
            raise Exception(f"Leanbot Controller start error: {error}")


    # ======================================================================
    # BLE Serial
    # ======================================================================

    def serial_notification_handler(self, sender, data):
        try:
            if(not self.serialBufferOpen):
                return

            text = data.decode(errors="replace")

            log("BLE RX", text)

            self.serialMessageQueue.put_nowait(text)   # Put one raw serial notification into the queue.

        except Exception as error:
            log(
                "BLE RX",
                f"BLE Serial error: {error}",
            )

    async def getSerialMessage(self) -> str:
        """
        Wait for and return one raw serial notification.
        """
        return await self.serialMessageQueue.get()

    def clearSerialMessageQueue(self) -> None:
        """
        Clear all pending serial messages from the queue.

        Messages are removed without waiting for new data.
        Each removed item is marked as done.
        """
        while True:
            try:
                self.serialMessageQueue.get_nowait()
                self.serialMessageQueue.task_done()
            except asyncio.QueueEmpty:
                break

    def clearSerialState(self) -> None:
        self.clearSerialMessageQueue()
        self.serialLineBuffer = ""

    def openSerial(self):
        self.serialBufferOpen = True

    def closeSerial(self):
        self.serialBufferOpen = False

    # def completeSerialMessage(self) -> None:
    #     self.serialMessageQueue.task_done()

    # ======================================================================
    # Serial Line Reader
    # ======================================================================

    async def getSerialLine(self) -> str:
        """
        Wait for and return the next complete serial line.
        """

        while True:

            # --------------------------------------------------------------
            # If buffer already contains a complete line, return it first.
            # --------------------------------------------------------------

            if "\n" in self.serialLineBuffer:

                line, self.serialLineBuffer = \
                    self.serialLineBuffer.split("\n", 1)

                return line.rstrip("\r")

            # --------------------------------------------------------------
            # Otherwise wait for another BLE notification.
            # --------------------------------------------------------------

            text = await self.getSerialMessage()

            self.serialLineBuffer += text

    # ======================================================================
    # Serial Message Waiter
    # ======================================================================

    async def waitSerialMessage(
        self,
        expected_message: str,
        handle_line: Optional[Callable[[str], Any]] = None,
        timeout_s: Optional[float] = None,
    ) -> bool:
        """
        Wait for a specific serial line.

        Every non-matching line can optionally be passed to handle_line.

        Args:
            expected_message:
                Exact serial line to wait for.

            handle_line:
                Optional callback for non-matching lines.
                The callback may be sync or async.

            timeout_s:
                Maximum time to wait.
                None means wait indefinitely.

        Returns:
            True when expected_message is received.

        Raises:
            TimeoutError:
                Expected message was not received within timeout_s.
        """

        async def wait_loop() -> bool:

            while True:

                line = await self.getSerialLine()

                log(
                    "RUN",
                    f"Serial line: {line}",
                )

                # ----------------------------------------------------------
                # Expected message
                # ----------------------------------------------------------

                if line == expected_message:
                    return True

                # ----------------------------------------------------------
                # Custom handler for other lines
                # ----------------------------------------------------------

                if handle_line is not None:

                    result = handle_line(line)

                    if inspect.isawaitable(result):
                        await result

        # ------------------------------------------------------------------
        # No timeout
        # ------------------------------------------------------------------

        if timeout_s is None:
            return await wait_loop()

        # ------------------------------------------------------------------
        # Timeout
        # ------------------------------------------------------------------

        try:

            async with asyncio.timeout(timeout_s):
                return await wait_loop()

        except TimeoutError as error:

            raise TimeoutError(
                f"Timeout waiting for serial message: "
                f"{expected_message}"
        ) from error

    # ------------------------------------------------------------------
    # BLE
    # ------------------------------------------------------------------

    async def find(self, scan_timeout=5, retry_interval=3):
        return await self.leanbot.find_device_by_name(
            scan_timeout=scan_timeout,
            retry_interval=retry_interval,
        )

    async def connect(self):
        return await self.leanbot.connect()

    async def disconnect(self):
        await self.leanbot.disconnect()

    def is_connected(self):
        return self.leanbot.is_connected()

    # ------------------------------------------------------------------
    # Bootloader
    # ------------------------------------------------------------------

    async def enterBootloader(self):
        await self.leanbot.uploader.attemptsEnterBootloader()

    async def keepOnBootloader(self):
        await self.leanbot.uploader.keepOnBootloader()

    async def escapeBootloader(self):
        await self.leanbot.uploader.escapeBootloader()

    def isBootloaderMode(self):
        return self.leanbot.uploader.is_bootloader_mode

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def isUploading(self):
        return self.is_uploading

    async def upload(self):
        """
        Upload firmware and keep the device in bootloader afterwards.
        """

        if self.is_uploading:
            raise RuntimeError("Upload is already running")

        self.is_uploading = True
        try:
            await self.leanbot.uploader.upload2()
            return True

        finally:
            self.is_uploading = False

    # ------------------------------------------------------------------
    # Upload progress
    # ------------------------------------------------------------------

    def getUploadWriteProgress(self):
        return self.leanbot.uploader.getWriteProgress()

    def getUploadVerifyProgress(self):
        return self.leanbot.uploader.getVerifyProgress()
    
    # ------------------------------------------------------------------
    # Firmware pipe
    # ------------------------------------------------------------------

    def open_hex_pipe(self):
        self.leanbot.uploader.open_hex_pipe()

    def push_hex_pipe(self, seq, addr, data):
        self.leanbot.uploader.push_hex_pipe(
            seq=seq,
            addr=addr,
            data=data,
        )

    def close_hex_pipe(self, reason=None):
        self.leanbot.uploader.close_hex_pipe(reason)

    def abort_upload(self, reason=None):
        self.leanbot.uploader.abort(reason)

    # ------------------------------------------------------------------
    # Serial
    # ------------------------------------------------------------------

    async def send(self, data, response=True):
        """
        Low-level serial send.

        This is intentionally generic for now.
        Higher-level commands can be added later, e.g.:

            await controller.run(...)
            await controller.stop(...)
            await controller.reset(...)
        """

        await self.leanbot.send(
            data,
            response=response,
        )

    # ------------------------------------------------------------------
    # Auto upload control code to leanbot
    # ------------------------------------------------------------------

    def get_hex_text(self, code_name: str) -> str:

        if not self._started:
            raise RuntimeError("LeanbotController.start() must be called first")

        hex_path = self.hex_map.get(code_name)

        if hex_path is None:
            raise FileNotFoundError(
                f"No compiled HEX found for: {code_name}"
            )

        return hex_path.read_text(encoding="utf-8")

    async def uploadLeanbotControlCode(self, code_name):
        if not self._started:
            raise RuntimeError("LeanbotController.start() must be called first")
        
        if self.is_uploading:
            raise RuntimeError('An upload operation is already in progress.')

        log('Controller', f'Upload {code_name}')

        hextext = self.get_hex_text(code_name)

        binary_data = convert_hex_to_bytearray(hextext)

        self.open_hex_pipe()
        self.push_hex_pipe(
            seq=0, 
            addr=0, 
            data=binary_data
        ) # push all binary data at once
        self.close_hex_pipe()

        await self.upload()

        log('Controller', f'Upload {code_name} Success')

        try:
            await self.escapeBootloader()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # High-level commands
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # LeanbotTinyRC (control leanbot back to its origin position)
    # ------------------------------------------------------------------

    async def uploadLeanbotRC(self) -> None:
        log('Controller', 'upload Leanbot Tiny RC')
        # reset leanbot
        # log('Controller', 'reset leanbot')
        # await self.disconnect()
        # await self.find(retry_interval=0.1)
        # await self.connect()

        # self.clearSerialState() # Display messages from Leanbot for debugging
        # self.openSerial()

        # version = self.config["LeanbotController"]["LeanbotTinyRC"]["Version"]
        # log('Controller', f'Wait for message: \"{version}\" in 1 second')

        # try:
        #     await self.waitSerialMessage(expected_message=version,timeout_s=1)
        # except TimeoutError:
        #     log('Controller', f'Not received \"{version}\" => wrong code')
        #     await self.uploadLeanbotControlCode('LeanbotTinyRC')
        await self.uploadLeanbotControlCode('LeanbotTinyRC')

    async def manualControlLeanbotRC(self):
        log('Controller', 'Start manual control Leanbot')
        await leanbotTinyRC.manual_control(self)

#####################################################################
# Helpers: Compile dir
#####################################################################

async def compile_directory(
    source_dir: str | Path,
    output_dir: str | Path,
    compile_server: str,
) -> dict[str, Path]:
    """
    Compile all .ino files in a directory concurrently.

    The old output directory is removed before compilation starts.

    If any compilation fails, the function raises an exception.
    """

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()

    # Remove the previous compilation output.
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # Create a clean output directory.
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all .ino files in the source directory.
    ino_files = list(source_dir.glob("*.ino"))

    if not ino_files:
        raise RuntimeError(
            f"No .ino files found in {source_dir}"
        )

    # Start all compilations concurrently.
    tasks = [
        asyncio.to_thread(
            compile_file,
            file_path,
            compile_server,
            output_dir,
        )
        for file_path in ino_files
    ]

    results = await asyncio.gather(*tasks)

    compiled_map = {}

    for ino_path, (success, hex_path) in zip(
        ino_files,
        results,
    ):
        if not success or hex_path is None:
            raise RuntimeError(
                f"Compilation failed: {ino_path.name}"
            )

        # Use the filename without the .ino extension as the key.
        compiled_map[ino_path.stem] = hex_path.resolve()

    return compiled_map