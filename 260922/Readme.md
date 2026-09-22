# Báo cáo công việc ngày 18/09/2026
## A. Công việc đã làm 
- Đã nhận thêm code của anh Thế Anh : Bổ sung hàm `spinSteps()` và sửa đổi `sendTinyRCCommand()` 
- Triển khai hàm `sendTinyRCCommand()` thay thế hàm gửi spam BLE Command đang sử dụng . 

### 1 Code bổ sung 
#### 1.1 Hàm `spinSteps()` : 
```cpp
void spinSteps(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int speed  = args.substring(0, pos).toInt();
  int rotationSteps = args.substring(pos + 1).toInt();

  LbMotion.stopAndWait();
  LbMotion.runLR(+speed, -speed);
  LbMotion.waitRotation(rotationSteps);
  LbMotion.stopAndWait();
}
```
- Nhận string `spst/<speed>/<rotationSteps>` và xuay Leanbot sao cho đạt số Steps tương ứng với <rotationSteps> . Tuy nhiên độ chính xác của góc suy ra không tỉ lệ tuyến tính với nhau mà còn phụ thuộc vào vận tốc xuay <speed>

- Hiện tại trong code `LeanbotTinyRC.ino` của Leanbot thì khi nhận lệnh BLE sẽ thực hiện 2 loại hàm điều khiển sau : 
  - Leanbot_run() : update liên tục giá trị vận tốc từ dữ liệu BLE command 
  ```cpp
  // Xử lý command r/60/70
    void Leanbot_run(String args) {

      int pos = args.indexOf('/');

      if (pos < 0)
        return;

      int left = args.substring(0, pos).toInt();
      int right = args.substring(pos + 1).toInt();

      LbMotion.runLR(left, right);
    }

    ```
    - runFwBw() : Thực hiện đi tiến lùi 1 lần, không spam vận tốc như hàm Leanbot_run().
    ```cpp
    // Xử lý command rfb/2000/700
    void runFwBw(String args) {

      int pos = args.indexOf('/');

      if (pos < 0)
        return;

      int speed = args.substring(0, pos).toInt();
      int durationMs = args.substring(pos + 1).toInt();

      LbMotion.stopAndWait();
      LbMotion.runLR(+speed, +speed);
      LbDelay(durationMs);
      LbMotion.stopAndWait();
      LbMotion.runLR(-speed, -speed);
      LbDelay(durationMs);
      LbMotion.stopAndWait();
    }
    ```
- Hiện tại sau khi nhận thêm code bổ sugn từ anh Thế Anh về việc thêm hàm `spinSteps()` thì em đang chưa biết có cần thay đổi cơ chế di chuyển hiện tại là gửi lệnh vận tốc liên tục bằng Leanbot_run() hay dùng spinSteps() để xuay từng khoảng bước step một ạ . 
- Em xin phép nhận thêm đề xuất từ Thầy ạ .

#### 1.2 Hàm `sendTinyRCCommand()`
- Code sau khi update mới từ anh Thế Anh : 

```python
async def sendTinyRCCommand(controller, command):
    # Start waiting for END before sending the first command.
    end_task = asyncio.create_task(
        controller.waitSerialMessage(f"{command}/END", 30) # wait maximum 30ms
    )

    try:
        # Retry up to 3 times if START is not received.
        for i in range(3):
            log("tinyRC", f"Send command {command} try {i + 1}")

            await controller.send(
                f"{command}\n",
                response=False,
            )

            # Wait up to 300 ms for START.
            if await controller.waitSerialMessage(
                f"{command}/START",
                0.3,
            ):
                log("tinyRC", "Receive command START")

                # START received -> wait for END.
                await end_task

                log("tinyRC", "Receive command END")
                return True

            log("tinyRC", "START timeout")

        # START was not received after 3 attempts.
        log(
            "tinyRC",
            "START not received after 3 attempts, "
            "cancelling END waiter",
        )

        return False

    finally:
        # Clean up END waiter if it is still waiting.
        if not end_task.done():
            end_task.cancel()

        await asyncio.gather(
            end_task,
            return_exceptions=True,
        )
```
- Hàm `sendTinyRCCommand()` sau khi sửa thực hiện các công việc sau : 
  - Tạo task chạy ngầm chờ nhận chuỗi verify "<command>/END" trong tối đa 30s.
  - Gửi lệnh và Retry tối đa 3 lần nếu không nhận được phản hồi "START" trong 0.3s (30ms).
  - Sau khi nhận được "START", đợi task "END" hoàn thành để đảm bảo Leanbot đã thực thi xong lệnh 
  - Tự động hủy và dọn dẹp task lắng nghe (cleanup trong `finally`) nếu timeout hoặc thất bại.

- Hàm được gọi trong code Inference với Camera như sau : 

```python

async def _async_loop(self):

  ....

            while self.running:
                cmd = None
                try:
                    while not self.cmd_queue.empty():
                        cmd = self.cmd_queue.get_nowait()
                except Exception:
                    pass
                
                if cmd is not None:
                    try:
                        # await self.leanbot.send(cmd, response=False) Code cũ gửi spam lệnh BLE mà ko đợi phản hồi verify 
                        await leanbotTinyRC.sendTinyRCCommand(self.leanbot, cmd) # Thay thế hàm mới có đợi verify trước khi gửi lệnh tiếp theo. 
                    except Exception as e:
                        print(f"[WARN] BLE send error: {e}")
                
                await asyncio.sleep(0.02)
        except Exception as e:
            print(f"[ERROR] Failed to connect BLE to Leanbot {self.leanbot_id}: {e}")
        finally:
              .......
```

- Kết quả log khi chạy triển khai như sau :
```

15:46:18.545 (   +0) [BLE] Serial line: r/500/106/START
15:46:18.545 (   +0) [BLE] Serial line: r/500/106/END
15:46:18.546 (   +0) [tinyRC] Receive command START
15:46:18.546 (   +0) [tinyRC] Receive command END
15:46:18.575 (  +29) [tinyRC] Send command r/433/78 try 1
15:46:18.634 (  +58) [BLE RX] r/433/78/START
r/43
15:46:18.634 (   +0) [BLE] Serial line: r/433/78/START
15:46:18.635 (   +0) [BLE RX] 3/78/END

15:46:18.635 (   +0) [BLE] Serial line: r/433/78/END
15:46:18.635 (   +0) [tinyRC] Receive command START
15:46:18.636 (   +0) [tinyRC] Receive command END
[INFO] Stopping Leanbot and disconnecting BLE Worker...
15:46:18.668 (  +32) [tinyRC] Send command r/0/0 try 1
15:46:18.701 (  +32) [BLE RX] r/0/0/START
r/0/0/E
15:46:18.702 (   +0) [BLE] Serial line: r/0/0/START
15:46:18.702 (   +0) [BLE RX] ND
15:46:18.702 (   +0) [BLE] Serial line: r/0/0/END

```


## B. Khó khăn 
- Không

## C. Công việc tiếp theo 
- Chỉnh góc sau khi đã đo được sai số so với target heading
- Chỉnh lại Kp ở Phase 2 để sai số tại phase3 là nhỏ nhất . 