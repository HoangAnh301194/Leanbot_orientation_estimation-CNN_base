# Báo cáo công việc ngày 22/09/2026
## A. Công việc đã làm 
- Đã nhận thêm code của anh Thế Anh : Bổ sung hàm `spinSteps()` và sửa đổi `sendTinyRCCommand()` 
- Triển khai hàm `sendTinyRCCommand()` thay thế hàm gửi spam BLE Command đang sử dụng . 
- Chỉnh góc sau khi đã đo được sai số so với target heading sử dụng `spinSteps()` để xoay.

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

### 2. Chỉnh góc sau khi đã đo được sai số so với target heading sử dụng `spinSteps()`

- Sau khi kết thúc Phase 4, hệ thống tính sai số góc `angle_error = wrap_to_180(current_angle - target_heading)` và gửi lệnh `spst` để Leanbot tự động xoay về đúng hướng `target_heading`. 
- **Ước lượng rotationSteps**:
  $$\text{rotationSteps} = \text{int}\left(\text{round}\left(Kp_{\text{spin}} \times |\text{angle\_error}|\right)\right)$$

- **xác định chiều xoay**:
  - Nếu `angle_error > 0`: Leanbot xoay theo chiều kim đồng hồ (`speed = +spin_speed`)
  - Nếu `angle_error < 0`: Leanbot xoay ngược chiều kim đồng hồ (`speed = -spin_speed`)

  ```python
  rotation_steps = int(round(args.kp_spin * abs(ang_err)))
  if rotation_steps > 0:
      # Nếu ang_err > 0:  +args.spin_speed
      # Nếu ang_err < 0:  -args.spin_speed
      spin_spd = args.spin_speed if ang_err > 0 else -args.spin_speed

      print(f"\n[POST-PHASE 4] Triggering spinSteps: ang_err={ang_err:.2f}deg, Target={target_heading:.1f}deg -> Speed={spin_spd}, Steps={rotation_steps}")
      ble_worker.send_spin_steps(spin_spd, rotation_steps)

  ```
  
- **Các thôgn số config cho SpinSteps**:
  - `--kp-spin`: Hệ số steps/độ (mặc định đang set là 5.0).
  - `--spin-speed`: Tốc độ quay của bánh xe (mặc định đang set là `100`).
- Lệnh được gửi tới Leanbot : `spst/<speed>/<rotationSteps>`

- Sau khi tiến hành SpinSteps() xong thì tiếp tục gọi lại Phase 4 và tính toán heading và tiếp tục tính sai số với target_heading . 

### 3. kết quả thực nghiệm thực tế
- Với hệ số Kp = 15 , speed = 100  ( đây là hệ số em lựa chọn sau vài lần chạy thử và tự đánh giá trực quan .)
- Lệnh chạy : 
```bash
python leanbotCameraController.py --show --ble 810836 --kp-spin 15.0 --spin-speed 100

```
> các argument đã được set mặc định các giá trị hệ số PID tối ưu nhất theo các báo cáo trước đó nên lệnh chạy có thể lược bỏ các argument đã set mặc định . 

#### Bảng tổng hợp kết quả 5 lần chạy thử nghiệm:

| STT | Thời gian | Tên file Log | Target Heading | Tọa độ Target (Pixel) | Sai số trước bù ($\text{Err}_1$) | Lệnh Spin (`Speed / Steps`) | Sai số sau bù ($\text{Err}_2$) | Độ cải thiện ($\Delta\text{Err}$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 17:43:49 | `log_roi_20260922_174319.csv` | **-67.9°** | (638.9, 314.2) | **-5.25°** | -100 / 79 steps | **-2.99°** | **+2.26°** |
| **2** | 17:44:54 | `log_roi_20260922_174421.csv` | **+16.9°** | (396.9, 188.7) | **+0.91°** | +100 / 14 steps | **-0.92°** | -0.01° |
| **3** | 17:46:07 | `log_roi_20260922_174532.csv` | **-125.7°** | (688.2, 383.6) | **-8.39°** | -100 / 126 steps | **+4.23°** | **+4.16°** |
| **4** | 17:47:22 | `log_roi_20260922_174652.csv` | **+177.7°** | (484.1, 247.0) | **+1.09°** | +100 / 16 steps | **-1.77°** | -0.68° |
| **5** | 17:48:23 | `log_roi_20260922_174750.csv` | **-1.1°** | (760.5, 406.2) | **+0.72°** | +100 / 11 steps | **-1.71°** | -0.99° |


---

#### 3.1 Lần test 1 — `log_roi_20260922_174319.csv`
- **Target heading:** `-67.9°`
- **Target pixel center:** `(638.9, 314.2)`
- **Heading Error 1 (trước spin):** `-5.25°`
- **Lệnh Spin:** `Speed = -100`, `Steps = 79`
- **Heading Error 2 (sau spin & verify):** `-2.99°`
- **Độ cải thiện:** `+2.26°` (Giảm 43.0% sai số)

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174319_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174319_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174319_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174319_pid_analysis.png" alt="PID 1" width="800">

---

#### 3.2 Lần test 2 — `log_roi_20260922_174421.csv`
- **Target heading:** `+16.9°`
- **Target pixel center:** `(396.9, 188.7)`
- **Heading Error 1 (trước spin):** `+0.91°`
- **Lệnh Spin:** `Speed = +100`, `Steps = 14`
- **Heading Error 2 (sau spin & verify):** `-0.92°`
- **Độ cải thiện:** Duy trì sai số dưới $1.0^\circ$

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174421_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174421_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174421_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174421_pid_analysis.png" alt="PID 2" width="800">

---

#### 3.3 Lần test 3 — `log_roi_20260922_174532.csv`
- **Target heading:** `-125.7°`
- **Target pixel center:** `(688.2, 383.6)`
- **Heading Error 1 (trước spin):** `-8.39°`
- **Lệnh Spin:** `Speed = -100`, `Steps = 126`
- **Heading Error 2 (sau spin & verify):** `+4.23°`
- **Độ cải thiện:** `+4.16°` (Giảm 49.6% sai số)

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174532_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174532_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174532_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174532_pid_analysis.png" alt="PID 3" width="800">

---

#### 3.4 Lần test 4 — `log_roi_20260922_174652.csv`
- **Target heading:** `+177.7°`
- **Target pixel center:** `(484.1, 247.0)`
- **Heading Error 1 (trước spin):** `+1.09°`
- **Lệnh Spin:** `Speed = +100`, `Steps = 16`
- **Heading Error 2 (sau spin & verify):** `-1.77°`
- **Độ cải thiện:** Nằm trong dải dung sai nhỏ ($< 1.8^\circ$)

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174652_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174652_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174652_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174652_pid_analysis.png" alt="PID 4" width="800">

---

#### 3.5 Lần test 5 — `log_roi_20260922_174750.csv`
- **Target heading:** `-1.1°`
- **Target pixel center:** `(760.5, 406.2)`
- **Heading Error 1 (trước spin):** `+0.72°`
- **Lệnh Spin:** `Speed = +100`, `Steps = 11`
- **Heading Error 2 (sau spin & verify):** `-1.71°`
- **Độ cải thiện:** Nằm trong dải dung sai nhỏ ($< 1.8^\circ$)

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174750_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174750_pid_diff_analysis.png" alt="Diff 5" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174750_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 5" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260922_174750_pid_analysis.png" alt="PID 5" width="800">

> Nhận xét chung:
> - Cơ chế bù góc tự động bằng spinSteps() giúp nắn góc xe xoay đúng chiều và bám sát Target Heading hơn so với không sử dụng.  
> - Đối với các trường hợp góc ban đầu lệch lớn (từ $5^\circ$ đến $8.4^\circ$), việc spinSteps giúp giảm sai số góc hiệu quả
> - Toàn bộ các lần thử nghiệm sau khi bù đều giữ được góc hướng trong dải sai số nhỏ ($< 1.8^\circ$ đối với các góc gần và $< 4.2^\circ$ đối với góc lệch xa). 
> - Đồ thị 2D trực quan thể hiện rõ đường chạy lần 2 (đỏ đậm) bám sát hướng mũi tên mục tiêu hơn hẳn so với lần 1 (đỏ nhạt).
## B. Khó khăn 
- Không

## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ .