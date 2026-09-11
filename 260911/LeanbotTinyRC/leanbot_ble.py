import asyncio
import time
import random
from bleak import BleakClient, BleakScanner
from logs import log

#####################################################################
# BLE serial function


class LeanbotBLE:

    CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

    def __init__(
        self,
        rx_buffer_size=1024,
        notify_callback=None,
        disconnect_callback=None,
        name="Leanbot 999999 BLE",
    ):
        self.__leanbotName = name
        self.__scanDevice = None
        self.__leanbotClient = None

        self.onMessage = notify_callback
        self.onDisconnected = disconnect_callback
        self.uploader = Uploader(self)
        self.onUploadForward = self.uploader.onForward

    def _on_notify_handler(self, sender, data):
        """
        Internal BLE notification handler routing data based on upload state.
        """
        if self.uploader.is_bootloader_mode:
            if self.onUploadForward is not None:
                self.onUploadForward(data)
        elif self.onMessage is not None:
            self.onMessage(sender, data)

    async def find_device_by_name(self, scan_timeout=5, retry_interval=3):
        log("BLE", f"Waiting for BLE device '{self.__leanbotName}'...")

        attempt = 0

        while True:
            attempt += 1

            try:
                log("BLE", f"Scan attempt #{attempt} " f"(timeout={scan_timeout}s)")

                device = await BleakScanner.find_device_by_filter(
                    lambda d, ad: d.name == self.__leanbotName
                    or (
                        ad.local_name is not None
                        and ad.local_name == self.__leanbotName
                    ),
                    timeout=scan_timeout,
                )

                if device:
                    self.__scanDevice = device

                    log(
                        "BLE", f"Found device: " f"{device.name} " f"[{device.address}]"
                    )

                    return device

                log(
                    "BLE",
                    f"'{self.__leanbotName}' not found. "
                    f"Retry after {retry_interval}s...",
                )

            except Exception as e:
                log("BLE", f"BLE scan error: {e}")

            await asyncio.sleep(retry_interval)

    async def connect(self):
        """
        Connect to scanned BLE device.
        """
        if self.__scanDevice is None:
            raise RuntimeError("No BLE device found")

        if self.is_connected() == True:
            log("BLE", "Already connected")
            return True

        try:
            log("BLE", f"Connecting to {self.__scanDevice.name}...")

            self.__leanbotClient = BleakClient(
                self.__scanDevice, disconnected_callback=self.onDisconnected
            )

            await self.__leanbotClient.connect()

            if self.__leanbotClient.is_connected:
                log("BLE", "Connected successfully")

                # Always start notify handler to handle both onMessage and onUploadForward
                await self.__leanbotClient.start_notify(
                    self.CHAR_UUID,
                    self._on_notify_handler,
                )

                return True

        except Exception as e:
            log("BLE", f"BLE connect error: {e}")
            self.__leanbotClient = None

        return False

    async def disconnect(self):
        """
        Disconnect BLE device.
        """
        if self.__leanbotClient is None:
            return

        try:
            if self.is_connected() == True:
                log("BLE", "Disconnecting...")
                await self.__leanbotClient.stop_notify(self.CHAR_UUID)
                await self.__leanbotClient.disconnect()
                log("BLE", "Disconnected")

        except Exception as e:
            log("ERR", f"BLE disconnect error: {e}")

        finally:
            self.__leanbotClient = None

    def is_connected(self):
        if self.__leanbotClient is None:
            return False
        return self.__leanbotClient.is_connected

    async def send(self, msg, response=True):
        if self.__leanbotClient is None:
            raise RuntimeError("BLE client not connected")

        if isinstance(msg, str):
            data = msg.encode()
        else:
            data = bytes(msg)

        await self.__leanbotClient.write_gatt_char(self.CHAR_UUID, data, response)

    async def uploadHexToLeanbot(self, pathToHex):

        # Load hex text
        with open(pathToHex, "r", encoding="utf-8") as f:
            hex_text = f.read()

        await self.uploader.upload(hex_text)


#####################################################################
# Upload function

# // total flash size - 32768 byte - 32 KB
ATMEGA328_TOTAL_FLASH_SIZE = 32768

# /*boothloader size*/
# // Using optiboothloader - total size = 512 byte
# // ref: https://github.com/Optiboot/optiboot

BOOTHLOADER_SIZE = 512
PAGE_SIZE_MAX = ATMEGA328_TOTAL_FLASH_SIZE - BOOTHLOADER_SIZE
BLOCK_SIZE = 128


REPORT_WRITE_STEP_BYTES = 1024
REPORT_READ_STEP_BYTES  = 4096

class Uploader:
    RESPONSE_ACK = [0x14, 0x10]  # SYNC - OK
    PAGE_SIZE_BYTE = 128
    LOAD_ADDRESS_TIMEOUT_MS = 1500
    WRITE_FLASH_TIMEOUT_MS = 750
    READ_FLASH_TIMEOUT_MS = 750
    GET_SYNC_TIMEOUT_MS = 1500

    def __init__(self, leanbot, rx_buffer_size=4096):
        self.leanbot = leanbot

        # Upload state
        self.total_bytes_data = 0
        # self.total_packets = 0

        self.is_bootloader_mode = False
        # self.upload_packets = []
        # self.page_buffer = bytearray()

        # Fixed-size ring buffer for responses during upload
        self.rx_buffer = bytearray(rx_buffer_size)
        self.rx_write = 0
        self.rx_read = 0
        self.rx_count = 0

        # Event used to stop bootloader keep-alive task
        self._data_event = asyncio.Event()
        self._bootloader_stop_event = asyncio.Event()
        self._bootloader_task = None

        # Event used to immediately abort upload
        self._abort_event = asyncio.Event()

        self.upload_packets = bytearray([0xFF]) * PAGE_SIZE_MAX
        self.hex_data_idx: int = 0
        self.last_block_available: int = 0
        self.pipeOpen = False

        self.writeBytes = 0
        self.readBytes = 0

    def abort(self, reason=None):
        if self._abort_event.is_set():
            return

        self._abort_event.set()

        # Wake any task waiting for either data or pipe state.
        self._data_event.set()

        log("UPLOAD", f"Upload aborted, reason = {reason}")

    ##################################################################################
    ## hexdata pipe interface

    def open_hex_pipe(self):
        self.pipeOpen = True
        # Reset upload context for a new upload.
        self.hex_data_idx = 0
        self.last_block_available = 0
        self.writeBytes = 0
        self.readBytes = 0

        log("UPLOAD", "Upload pipe opened")

    def push_hex_pipe(self, seq, addr, data):

        try:
            if not self.pipeOpen:
                raise RuntimeError("Upload pipe is not open")

            data_length = len(data)

            # --------------------------------------------------------------
            # Validate address
            # --------------------------------------------------------------

            if addr < 0:
                raise ValueError(f"Invalid UPLOAD address: {addr}")

            end_addr = addr + data_length

            if end_addr > PAGE_SIZE_MAX:
                raise ValueError(
                    f"UPLOAD out of buffer range: "
                    f"addr=0x{addr:04X}, "
                    f"length={data_length}, "
                    f"end=0x{end_addr:04X}, "
                    f"max=0x{PAGE_SIZE_MAX:04X}"
                )

            # --------------------------------------------------------------
            # Save previous watermark/index BEFORE updating
            # --------------------------------------------------------------

            previous_idx = self.hex_data_idx

            # --------------------------------------------------------------
            # Store raw packet data directly at absolute address
            # --------------------------------------------------------------

            self.upload_packets[addr:end_addr] = data

            if end_addr > self.hex_data_idx:
                self.hex_data_idx = end_addr

            # --------------------------------------------------------------
            # Update 128-byte block watermark
            # --------------------------------------------------------------

            if previous_idx // BLOCK_SIZE != self.hex_data_idx // BLOCK_SIZE:
                self.last_block_available = (
                    self.hex_data_idx // BLOCK_SIZE
                ) * BLOCK_SIZE

            # --------------------------------------------------------------
            # Clear next 128 bytes
            # --------------------------------------------------------------

            clear_end = min(PAGE_SIZE_MAX, self.hex_data_idx + BLOCK_SIZE)

            self.upload_packets[self.hex_data_idx : clear_end] = b"\xFF" * (
                clear_end - self.hex_data_idx
            )

            log(
                "UPLOAD",
                f"UPLOAD stored: "
                f"seq={seq}, "
                f"addr=0x{addr:04X}, "
                f"len={data_length}, "
                f"end=0x{end_addr:04X}, "
                f"hexData_idx={self.hex_data_idx}, "
                f"lastBlockAvailable={self.last_block_available}",
            )
        except Exception as error:
            self.close_hex_pipe(error)
            raise error

    def close_hex_pipe(self, reason=None):

        if not self.pipeOpen:
            return

        previous_idx = self.hex_data_idx

        # received last seq => maintain proper block alignment for flash writing.
        if self.hex_data_idx % BLOCK_SIZE != 0:
            start_idx = (self.hex_data_idx // BLOCK_SIZE) * BLOCK_SIZE
            self.hex_data_idx = start_idx + BLOCK_SIZE

        # EOF alignment may create one additional writable 128-byte block.
        if previous_idx // BLOCK_SIZE != self.hex_data_idx // BLOCK_SIZE:
            self.last_block_available = (
                self.hex_data_idx // BLOCK_SIZE
            ) * BLOCK_SIZE

        self.pipeOpen = False

        if reason is not None:
            log("UPLOAD", f"Stop upload, data error: {reason}")
            self.abort(reason)
            return

        log("UPLOAD", "Received All data")

    ##################################################################################

    def onForward(self, data):
        """
        Callback to append incoming notification data into rx_buffer when uploading.
        """
        for b in data:
            self.rx_buffer[self.rx_write] = b

            self.rx_write += 1
            if self.rx_write >= len(self.rx_buffer):
                self.rx_write = 0

            if self.rx_count < len(self.rx_buffer):
                self.rx_count += 1
            else:
                # Buffer full -> overwrite oldest byte
                self.rx_read += 1
                if self.rx_read >= len(self.rx_buffer):
                    self.rx_read = 0

        self._data_event.set()

    def reset_rx_buffer(self):
        """
        Clear the rx ring buffer state.
        """
        self.rx_write = 0
        self.rx_read = 0
        self.rx_count = 0
        self._data_event.clear()

    async def wait_data(self, n_bytes, timeout_ms=1000):
        """
        Wait until rx_buffer has at least n_bytes.
        """
        start_time = time.perf_counter()
        timeout_sec = timeout_ms / 1000.0

        while self.rx_count < n_bytes:
            elapsed = time.perf_counter() - start_time
            remaining = timeout_sec - elapsed

            if remaining <= 0:
                raise TimeoutError(f"Need {n_bytes} bytes, got {self.rx_count}")

            self._data_event.clear()

            if self.rx_count >= n_bytes:
                break

            try:
                await asyncio.wait_for(self._data_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                if self.rx_count >= n_bytes:
                    break
                raise TimeoutError(f"Need {n_bytes} bytes, got {self.rx_count}")

    def get_nbytes_rx_data(self, n_bytes):
        """
        Extract n_bytes from rx_buffer.
        """
        if self.rx_count < n_bytes:
            raise ValueError(
                f"Requested {n_bytes} bytes, but only {self.rx_count} available"
            )

        result = bytearray()

        for _ in range(n_bytes):
            result.append(self.rx_buffer[self.rx_read])

            self.rx_read += 1
            if self.rx_read >= len(self.rx_buffer):
                self.rx_read = 0

            self.rx_count -= 1

        log("Wait", result.hex(" "))
        return bytes(result)

    def isACK(self, bytes_data):
        if len(bytes_data) != 2:
            return False

        return (
            bytes_data[0] == self.RESPONSE_ACK[0]
            and bytes_data[1] == self.RESPONSE_ACK[1]
        )

    async def enterBootloader(self):

        if self.leanbot.is_connected():
            log("Upload", "Disconnecting....")
            await self.leanbot.disconnect()
            await asyncio.sleep(3.5)

        log("Upload", "Reconnecting to enter bootloader...")
        success = await self.leanbot.connect()
        log("Upload", f"is reconnect success: {success}")

        if success != True:
            raise RuntimeError("Reconnect failed")

        self.reset_rx_buffer()

        await asyncio.sleep(0.04)

        self.is_bootloader_mode = True
        log("Upload", "Wait for getSync to enter bootloader...")

        await self.send_and_wait_sync()

        log("Upload", "Entered bootloader successfully!")

    async def attemptEnterBootloader(self, MAX_ATTEMPTS=3):
        log("UPLOAD", "Enter bootloader")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                log("UPLOAD", f"Enter bootloader attempt {attempt}")

                await self.enterBootloader()

                log(
                    "UPLOAD",
                    f"Enter bootloader success on attempt {attempt}, "
                    f"now in bootloader mode",
                )

                break

            except Exception as e:
                log("UPLOAD", f"Enter bootloader attempt {attempt} failed: {e}")

                if attempt == MAX_ATTEMPTS:
                    raise RuntimeError(
                        f"Cannot enter bootloader after " f"{MAX_ATTEMPTS} attempts"
                    ) from e

    async def keepOnBootloader(self):
        self._bootloader_stop_event.clear()

        self._keep_bootloader_task = asyncio.current_task()

        log("UPLOAD", "Keep bootloader alive")

        try:
            while not self._bootloader_stop_event.is_set():
                await self.send_and_wait_sync()

                try:
                    await asyncio.wait_for(
                        self._bootloader_stop_event.wait(),
                        timeout=0.25,
                    )
                except asyncio.TimeoutError:
                    pass

        finally:
            self._keep_bootloader_task = None
            log("UPLOAD", "Stop keeping bootloader alive")
 
    async def escapeBootloader(self):
        log("UPLOAD", "Escape bootloader requested")

        self._bootloader_stop_event.set()

        task = self._keep_bootloader_task

        if task is not None and task is not asyncio.current_task():
            await task

        self.is_bootloader_mode = False

        log("UPLOAD", "Bootloader keep-alive stopped")

    async def upload2(self):
        # self.is_bootloader_mode = True

        t1 = time.perf_counter()

        try:
            await self.attemptEnterBootloader()

            log("UPLOAD", "Start upload")

            self.total_bytes_data = 0

            log("UPLOAD", "Start write pages")

            await self.write_all_pages2()

            log("UPLOAD", "Start verify pages")

            await self.verify_uploaded_code2()

            log("UPLOAD", "Upload done")

            return True

        finally:
            t2 = time.perf_counter()

            log("UPLOAD", f"Elapsed: {t2 - t1:.3f}s")

            # await self.KeepOnBootloader()

    async def send_and_wait_sync(self, timeout_ms = GET_SYNC_TIMEOUT_MS):
        """
        Send STK500 GET_SYNC command and wait for ACK.

        Ref:
        https://ww1.microchip.com/downloads/en/Appnotes/doc2591.pdf
        """

        get_sync_cmd = bytes([0x30, 0x20])

        log("SYNC", "Send GET_SYNC command")

        await self.leanbot.send(get_sync_cmd, response=True)

        await self.wait_data(2, timeout_ms=timeout_ms)
        respond = self.get_nbytes_rx_data(2)

        if not self.isACK(respond):
            log("SYNC", f"Invalid ACK: {respond.hex(' ')}")
            raise RuntimeError("Get sync failed")

        log("SYNC", "SYNC ACK received")

    def is_read_flash_ack(self, data):
        """
        Expected:
            INSYNC | page_data... | OK
        """

        expected_size = self.PAGE_SIZE_BYTE + 2

        if len(data) != expected_size:
            return False

        return data[0] == self.RESPONSE_ACK[0] and data[-1] == self.RESPONSE_ACK[1]

    async def read_flash(self, page_index=0):
        """
        Read one flash page.
        """

        # 1) LOAD_ADDRESS
        byte_address = page_index * self.PAGE_SIZE_BYTE

        word_address = byte_address >> 1
        addr_low = word_address & 0xFF
        addr_high = (word_address >> 8) & 0xFF

        load_address_cmd = bytes([0x55, addr_low, addr_high, 0x20])

        # 2) read page: STK_READ_PAGE + len_hi + len_lo + 'F' + STK_CRC_EOP
        page_size = self.PAGE_SIZE_BYTE

        read_page_cmd = bytes([0x74, 0x00, page_size, 0x46, 0x20])

        read_page_payload = load_address_cmd + read_page_cmd

        log("READ", f"Send READ_PAGE page={page_index}")

        await self.leanbot.send(read_page_payload, response=True)

        await self.wait_data(page_size + 4, timeout_ms=self.READ_FLASH_TIMEOUT_MS)
        respond = self.get_nbytes_rx_data(page_size + 4)

        if not self.isACK(respond[:2]) or not self.is_read_flash_ack(respond[2:]):
            log("READ", f"Invalid response: {respond.hex(' ')}")
            raise RuntimeError("Read flash failed")

        log("READ", "READ_PAGE ACK received")

        # remove sync-ok of load address
        respond = respond[2:]

        # Remove INSYNC and OK bytes
        return respond[1:-1]

    async def write_flash(self, page_index, page_data):
        """
        Write one flash page.

        Ref:
        https://ww1.microchip.com/downloads/en/Appnotes/doc2591.pdf
        """

        if (
            not isinstance(page_data, (bytes, bytearray))
            or len(page_data) != Uploader.PAGE_SIZE_BYTE
        ):
            raise ValueError(f"page_data must be {Uploader.PAGE_SIZE_BYTE} bytes")

        # 1) LOAD_ADDRESS
        byte_address = page_index * self.PAGE_SIZE_BYTE

        word_address = byte_address >> 1
        addr_low = word_address & 0xFF
        addr_high = (word_address >> 8) & 0xFF

        load_address_cmd = bytes([0x55, addr_low, addr_high, 0x20])

        # 2) STK_PROG_PAGE
        prog_page_header = bytes([0x64, 0x00, Uploader.PAGE_SIZE_BYTE, 0x46])
        prog_page_tail = bytes([0x20])

        prog_page_payload = (
            load_address_cmd + prog_page_header + bytes(page_data) + prog_page_tail
        )

        half = 120  # half 1: 120 bytes, half 2: 17 bytes.

        log("WRITE", f"Send PROG_PAGE page={page_index}")

        await self.leanbot.send(prog_page_payload[:half], response=False)
        await self.leanbot.send(prog_page_payload[half:], response=True)

        await self.wait_data(4, timeout_ms=Uploader.WRITE_FLASH_TIMEOUT_MS)
        respond = self.get_nbytes_rx_data(4)

        if not self.isACK(respond[:2]) or not self.isACK(respond[2:]):
            log("WRITE", f"Invalid ACK: {respond.hex(' ')}")
            raise RuntimeError("Write flash failed")

        log("WRITE", f"Page {page_index} written")

    async def write_all_pages2(self):
        t1 = time.perf_counter()

        try:
            write_idx = 0

            while True:

                # ----------------------------------------------------------
                # External abort signal
                # ----------------------------------------------------------

                if self._abort_event.is_set():
                    raise RuntimeError("Upload aborted")

                # ----------------------------------------------------------
                # Input pipe is closed and all available data has been
                # written.
                #
                # last_block_available is already rounded up to BLOCK_SIZE
                # when close_hex_pipe() is called.
                # ----------------------------------------------------------

                if not self.pipeOpen and write_idx >= self.last_block_available:
                    log("UPLOAD", "Write pages done")
                    break

                # ----------------------------------------------------------
                # No complete 128-byte page is available yet.
                #
                # Keep the original behavior: provider can continue pushing
                # data asynchronously.
                # ----------------------------------------------------------

                if write_idx >= self.last_block_available:
                    await asyncio.sleep(0)
                    continue

                # ----------------------------------------------------------
                # Protect bootloader area
                # ----------------------------------------------------------

                if write_idx >= PAGE_SIZE_MAX:
                    raise RuntimeError("Address write overlaps bootloader space")

                # ----------------------------------------------------------
                # Extract exactly one 128-byte page from the firmware image.
                # ----------------------------------------------------------

                page_data = self.upload_packets[write_idx : write_idx + BLOCK_SIZE]

                if len(page_data) != BLOCK_SIZE:
                    raise RuntimeError(
                        f"Invalid page data size: "
                        f"address=0x{write_idx:04X}, "
                        f"size={len(page_data)}"
                    )

                page_index = write_idx // BLOCK_SIZE

                await self.write_flash(page_index, page_data)

                write_idx += BLOCK_SIZE
                self.writeBytes = write_idx

                if(write_idx % REPORT_WRITE_STEP_BYTES == 0):
                    log("UPLOAD", f"Write {write_idx} bytes")

            self.total_bytes_data = self.writeBytes
            if(self.writeBytes % REPORT_WRITE_STEP_BYTES != 0):
                log("UPLOAD", f"Write {self.writeBytes} bytes"); # Extra last write message
        finally:
            t2 = time.perf_counter()
            log("UPLOAD", f"Write all pages completed in {t2 - t1:.3f}s")

    def getWriteProgress(self):
        return self.writeBytes

    async def verify_uploaded_code2(self, mode="sample"):
        """
        Verify uploaded flash data.

        mode:
            "full"   -> verify all written pages
            "sample" -> verify about 1/16 random written pages
        """

        t1 = time.perf_counter()

        try:
            # ----------------------------------------------------------
            # Determine number of pages actually written.
            #
            # close_hex_pipe() already rounds hex_data_idx up to PAGE_SIZE_BYTE
            # so this is always page-aligned when input is finished.
            # ----------------------------------------------------------

            total_pages = self.hex_data_idx // self.PAGE_SIZE_BYTE

            if total_pages == 0:
                raise RuntimeError("No pages to verify")

            if mode == "full":
                page_indices = list(range(total_pages))

                log("VERIFY", f"Mode FULL: verifying {total_pages} pages")

            elif mode == "sample":
                sample_count = max(1, total_pages // 16)

                page_indices = random.sample(range(total_pages), sample_count)

                log(
                    "VERIFY",
                    f"Mode SAMPLE: verifying " f"{sample_count}/{total_pages} pages",
                )

            else:
                raise ValueError(f'Invalid mode "{mode}"')

            # ----------------------------------------------------------
            # Verify each selected page
            # ----------------------------------------------------------
            verifyStep = 0

            for page_index in page_indices:

                page_start = page_index * self.PAGE_SIZE_BYTE
                page_end = page_start + self.PAGE_SIZE_BYTE

                expected = self.upload_packets[page_start:page_end]

                if len(expected) != self.PAGE_SIZE_BYTE:
                    raise RuntimeError(
                        f"Invalid expected page size: "
                        f"page={page_index}, "
                        f"size={len(expected)}"
                    )

                log("VERIFY", f"Reading page {page_index}")

                device_data = await self.read_flash(page_index)

                if not self.compare_page(expected, device_data):

                    log("VERIFY", f"Page {page_index} MISMATCH")

                    for i, (exp, act) in enumerate(zip(expected, device_data)):
                        if exp != act:
                            log(
                                "VERIFY",
                                f"Page {page_index}, "
                                f"offset {i}: "
                                f"expected 0x{exp:02X}, "
                                f"got 0x{act:02X}",
                            )
                            break

                    raise RuntimeError(f"Verify page {page_index} failed")

                log("VERIFY", f"Page {page_index} OK")

                verifyStep += 1
                self.readBytes = round(verifyStep * self.total_bytes_data / len(page_indices))
                if verifyStep == len(page_indices):
                    self.readBytes = self.total_bytes_data

                log(
                    "UPLOAD",
                    f"Verify {self.readBytes}/{self.total_bytes_data} bytes"
                )

            log("VERIFY", f"Verification SUCCESS ({mode})")

        except Exception:
            log("VERIFY", f"Verification FAILED ({mode})")
            raise

        finally:
            t2 = time.perf_counter()
            log("VERIFY", f"Completed in {t2 - t1:.3f}s")

    def getVerifyProgress(self):
        return self.readBytes

    def compare_page(self, expected, actual):
        if expected is None or actual is None:
            return False

        return expected == actual
