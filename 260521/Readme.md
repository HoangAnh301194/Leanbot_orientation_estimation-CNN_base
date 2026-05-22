# Báo cáo công việc ngày 21/05/2026

## A. Công việc đã làm
- Tìm hiểu về loss function: Cross Entropy và Binary Cross Entropy
- Tìm hiểu cách tùy chỉnh Loss Function trong YOLO

### 1. Bản chất quá trình huấn luyện model

Trong học máy và học sâu, một mô hình được xây dựng để học mối quan hệ giữa dữ liệu đầu vào và kết quả mong muốn. Với một mẫu dữ liệu đầu vào `x`, mô hình sẽ sinh ra một kết quả dự đoán `ŷ`. Kết quả dự đoán này sau đó được so sánh với nhãn thật `y` để đánh giá mức độ sai lệch của mô hình.

Quá trình này có thể mô tả tổng quát như sau:

```text
x -> model -> ŷ
```

Trong đó:

- `x`: dữ liệu đầu vào, ví dụ ảnh, tín hiệu cảm biến hoặc vector đặc trưng.
- `y`: nhãn thật hoặc giá trị mong muốn.
- `ŷ`: kết quả mô hình dự đoán.
- `model`: hàm ánh xạ từ đầu vào sang đầu ra, có các tham số cần học.

Mục tiêu của quá trình huấn luyện là điều chỉnh các tham số của mô hình sao cho kết quả dự đoán `ŷ` càng gần với nhãn thật `y` càng tốt.

Một vòng huấn luyện cơ bản gồm các bước:

1. Đưa dữ liệu đầu vào vào mô hình.
2. Mô hình sinh ra kết quả dự đoán.
3. So sánh kết quả dự đoán với nhãn thật.
4. Tính toán sai số thông qua loss function.
5. Cập nhật tham số mô hình để giảm sai số.
6. Lặp lại quá trình trên qua nhiều epoch.

Có thể biểu diễn ngắn gọn:

```text
Input -> Prediction -> Loss -> Backpropagation -> Update Parameters
```

Trong đó, loss function đóng vai trò trung tâm vì nó cho mô hình biết mức độ dự đoán sai là bao nhiêu.

---

### 2. Loss function

Loss function, hay hàm mất mát, là hàm dùng để đo mức độ sai lệch giữa kết quả dự đoán của mô hình và nhãn thật.

Có thể hiểu đơn giản:

```math
\mathrm{Loss} = f(y, \hat{y})
```

Trong đó:

- `y`: nhãn thật.
- `ŷ`: kết quả dự đoán.
- `Loss`: giá trị thể hiện mức độ sai lệch.

Nếu mô hình dự đoán đúng hoặc gần đúng, giá trị loss sẽ nhỏ. Nếu mô hình dự đoán sai nhiều, giá trị loss sẽ lớn.

Mục tiêu của quá trình huấn luyện là tối thiểu hóa giá trị loss:

```math
\min \mathrm{Loss}
```

Nói cách khác, training model chính là quá trình tìm bộ tham số sao cho loss đạt giá trị nhỏ nhất có thể.

Tùy theo dạng bài toán, ta cần chọn loss function phù hợp. Ví dụ:

- Bài toán hồi quy: thường dùng MAE, MSE.
- Bài toán phân loại nhị phân: thường dùng Binary Cross Entropy.
- Bài toán phân loại nhiều lớp: thường dùng Cross Entropy.

---

### 3. Vai trò của loss function

Loss function có vai trò như một tín hiệu phản hồi cho mô hình trong quá trình học.

Sau mỗi lần dự đoán, loss function cho biết mô hình đang sai bao nhiêu. Dựa trên giá trị loss này, thuật toán tối ưu như Gradient Descent sẽ điều chỉnh các tham số của mô hình theo hướng làm giảm loss.

Quy trình tổng quát:

```text
Prediction -> Loss -> Gradient -> Update
```

Cụ thể:

1. Mô hình nhận ảnh đầu vào.
2. Mô hình dự đoán class hoặc xác suất của các class.
3. Loss function so sánh dự đoán với nhãn thật.
4. Backpropagation tính gradient của loss theo các tham số mô hình.
5. Optimizer cập nhật trọng số để giảm loss.
6. Sau nhiều lần lặp, mô hình học được cách dự đoán tốt hơn.

Do đó, loss function không chỉ là công thức tính sai số, mà còn định hướng cách mô hình học.

Nếu chọn loss function không phù hợp, mô hình có thể học sai mục tiêu. Ví dụ, với bài toán phân loại nhiều class nhưng lại dùng loss theo kiểu hồi quy đơn giản, mô hình có thể không học tốt đặc trưng phân biệt giữa các class. Ngược lại, với bài toán dự đoán giá trị liên tục nhưng lại ép thành phân loại, kết quả có thể thiếu chính xác nếu số class không đủ mịn.

---

### 4. Loss function cho bài toán phân loại

Bài toán phân loại là bài toán dự đoán một mẫu dữ liệu thuộc về class nào.

Ví dụ:

- Ảnh có Leanbot hay không.
- Leanbot thuộc một trong các class góc như `0`, `p15`, `m15`, `p30`, ...
- Ảnh thuộc class `Leanbot_0`, `Leanbot_p15` hay `Leanbot_m15`.
- Leanbot thuộc nhóm class gần `p45`, `p60` hay `p75`.

Trong bài toán phân loại, đầu ra của mô hình thường liên quan tới xác suất. Mô hình không chỉ đưa ra một class, mà thường đưa ra điểm số hoặc xác suất cho từng class.

Có ba dạng phân loại phổ biến:

#### 4.1. Binary classification

Binary classification là bài toán phân loại nhị phân, chỉ có hai khả năng:

```math
y \in \{0, 1\}
```

Ví dụ:

- Ảnh có Leanbot hay không.
- Ảnh có thuộc class góc `p45` hay không.
- Ảnh có thuộc nhóm góc phía trước của Leanbot hay không.

Loss thường dùng: Binary Cross Entropy.

#### 4.2. Multi-class classification

Multi-class classification là bài toán có nhiều class, nhưng mỗi mẫu chỉ thuộc về một class duy nhất.

Ví dụ:

- Góc Leanbot thuộc một trong 24 class.
- Leanbot thuộc một trong các class như `Leanbot_0`, `Leanbot_p15`, `Leanbot_m15`, ...
- Một ảnh chỉ có thể rơi vào đúng một góc trong 24 góc của Leanbot.

Loss thường dùng: Cross Entropy.

#### 4.3. Multi-label classification

Multi-label classification là bài toán mà một mẫu có thể có nhiều nhãn đúng cùng lúc.

Ví dụ một ảnh có thể đồng thời có:

- class góc `p45`
- ảnh đủ sáng
- ROI đã crop đúng
- Leanbot không bị che khuất

Với dạng này, mỗi nhãn được xem như một bài toán đúng/sai độc lập.

Loss thường dùng: Binary Cross Entropy.

---

### 5. Binary Cross Entropy

#### 5.1. Định nghĩa

Binary Cross Entropy, viết tắt là BCE, là loss function thường dùng cho bài toán phân loại nhị phân hoặc multi-label classification.

Trong bài toán nhị phân, nhãn thật có dạng:

```math
y \in \{0, 1\}
```

Trong đó:

- `y = 1`: mẫu thuộc class cần dự đoán.
- `y = 0`: mẫu không thuộc class đó.

Mô hình thường dự đoán ra một xác suất:

```math
p \in [0, 1]
```

Trong đó:

- `p`: xác suất mô hình dự đoán mẫu thuộc class 1.
- `1-p`: xác suất mô hình dự đoán mẫu thuộc class 0.

Ví dụ:

```text
p = 0.9
```

có nghĩa là mô hình dự đoán xác suất mẫu thuộc class 1 là 90%.

---

#### 5.2. Công thức

Công thức Binary Cross Entropy:

```math
\mathrm{BCE} = -\left[ y \log(p) + (1-y)\log(1-p) \right]
```

Trong đó:

- `y`: nhãn thật, nhận giá trị 0 hoặc 1.
- `p`: xác suất mô hình dự đoán mẫu thuộc class 1.
- `log`: hàm logarit tự nhiên.

Công thức này có thể xét theo hai trường hợp.

##### 5.2.1. Trường hợp nhãn thật là 1

Khi `y = 1`:

```math
\mathrm{BCE} = -\log(p)
```

Nếu mô hình dự đoán:

```text
p = 0.9
```

thì loss nhỏ, vì mô hình dự đoán đúng với độ tin cậy cao.

Nếu mô hình dự đoán:

```text
p = 0.1
```

thì loss lớn, vì mô hình dự đoán sai với độ tin cậy cao.

##### 5.2.2. Trường hợp nhãn thật là 0

Khi `y = 0`:

```math
\mathrm{BCE} = -\log(1-p)
```

Nếu mô hình dự đoán:

```text
p = 0.1
```

thì:

```text
1-p = 0.9
```

loss nhỏ, vì mô hình dự đoán đúng rằng mẫu không thuộc class 1.

Nếu mô hình dự đoán:

```text
p = 0.9
```

thì:

```text
1-p = 0.1
```

loss lớn, vì mô hình dự đoán sai với độ tin cậy cao.

---

#### 5.3. Ý nghĩa

Binary Cross Entropy không chỉ đánh giá mô hình đúng hay sai, mà còn đánh giá mức độ tự tin của mô hình.

Nếu mô hình dự đoán đúng nhưng chưa tự tin, loss vẫn còn tương đối lớn. Nếu mô hình dự đoán đúng và tự tin, loss nhỏ. Nếu mô hình dự đoán sai nhưng rất tự tin, loss sẽ rất lớn.

Điều này phù hợp với bài toán phân loại xác suất, vì mô hình cần không chỉ dự đoán đúng class, mà còn cần đưa ra xác suất hợp lý.

Ví dụ:

| Nhãn thật | Dự đoán của mô hình | Ý nghĩa | Loss |
|---|---:|---|---|
| `y=1` | `p=0.9` | Đúng và tự tin | Nhỏ |
| `y=1` | `p=0.6` | Đúng nhưng chưa tự tin | Trung bình |
| `y=1` | `p=0.1` | Sai và tự tin | Lớn |
| `y=0` | `p=0.1` | Đúng và tự tin | Nhỏ |
| `y=0` | `p=0.9` | Sai và tự tin | Lớn |

---

#### 5.4. Hàm activation đi kèm: Sigmoid

BCE thường đi kèm với hàm Sigmoid.

Hàm Sigmoid có công thức:

```math
\sigma(z) = \frac{1}{1 + e^{-z}}
```

Trong đó:

- `z`: output thô của mô hình, còn gọi là logit.
- `sigma(z)`: xác suất sau khi đi qua Sigmoid.

Sigmoid biến một giá trị bất kỳ từ `(-infinity, +infinity)` về khoảng `(0, 1)`.

Ví dụ:

- Nếu `z` rất lớn, `sigma(z)` gần 1.
- Nếu `z` rất nhỏ, `sigma(z)` gần 0.
- Nếu `z = 0`, `sigma(z) = 0.5`.

Do đó, Sigmoid phù hợp cho bài toán nhị phân vì nó tạo ra xác suất thuộc class 1.

Trong PyTorch, thay vì tự dùng Sigmoid rồi đưa vào BCELoss, ta thường dùng:

```python
torch.nn.BCEWithLogitsLoss()
```

Hàm này đã gộp sẵn:

```text
Sigmoid + Binary Cross Entropy
```

Vì vậy, khi dùng `BCEWithLogitsLoss`, không nên tự thêm Sigmoid ở cuối model trước khi tính loss.

---

#### 5.5. Khi nào dùng BCE?

BCE phù hợp trong các trường hợp:

1. Bài toán phân loại nhị phân:

```text
Có Leanbot? -> Có / Không
```

2. Bài toán multi-label:

```text
Ảnh là class p45? ROI đúng? đủ sáng? không bị che khuất?
```

3. Mỗi nhãn là một quyết định đúng/sai độc lập.

Tuy nhiên, BCE không phải lựa chọn tự nhiên nhất cho bài toán multi-class mà mỗi ảnh chỉ thuộc một class duy nhất. Ví dụ, nếu ảnh Leanbot chỉ có một góc đúng trong 24 góc, thì bài toán này phù hợp hơn với Cross Entropy.

---

### 6. Cross Entropy

#### 6.1. Định nghĩa

Cross Entropy, viết tắt là CE, là loss function thường dùng cho bài toán multi-class classification.

Trong bài toán multi-class classification, có nhiều class nhưng mỗi mẫu chỉ thuộc về một class duy nhất.

Ví dụ bài toán phân loại góc Leanbot:

```text
0, p15, m15, p30, m30, p45, m45, ..., p165, 180, p195
```

Nếu mỗi ảnh Leanbot chỉ có một góc đúng, thì đây là bài toán multi-class classification.

---

#### 6.2. Cách biểu diễn nhãn thật

Giả sử bài toán có nhiều class. Ở đây, `class` có thể hiểu đơn giản là một nhãn cần phân biệt, ví dụ `0`, `p15`, `m15`, `p30`, ...

Nhãn thật có thể viết dưới dạng một dãy số để chỉ ra class đúng. Cách viết này thường được gọi là `one-hot vector`.

Hiểu đơn giản, `one-hot vector` là một dãy gồm nhiều số `0` và chỉ có đúng một số `1`. Số `1` nằm ở vị trí của class đúng.

Ví dụ lấy 4 class đại diện trong bài toán Leanbot:

```text
[0, p15, m15, p30]
```

Nếu nhãn thật là `p15`, dãy nhãn sẽ là:

```text
y = [0, 1, 0, 0]
```

Nếu nhãn thật là `m15`, dãy nhãn sẽ là:

```text
y = [0, 0, 1, 0]
```

Trong dãy này, vị trí của class đúng có giá trị `1`, còn các vị trí khác có giá trị `0`.

Tuy nhiên, trong nhiều thư viện như PyTorch, `CrossEntropyLoss` thường không cần nhận cả dãy này, mà chỉ cần nhận số thứ tự của class đúng.

Ví dụ:

```python
# Ví dụ 4 class: 0, p15, m15, p30
target = 1  # nghĩa là class p15
```

---

#### 6.3. Đầu ra của mô hình

Với bài toán multi-class, mô hình thường sinh ra một vector điểm số thô, gọi là logits.

Ví dụ với 4 class đại diện:

```text
z = [0.3, 2.5, 1.1, -0.4]
```

Các giá trị này chưa phải xác suất. Để biến logits thành xác suất, ta dùng hàm Softmax.

---

#### 6.4. Hàm Softmax

Softmax biến vector logits thành phân phối xác suất trên các class.

Công thức Softmax:

```math
\operatorname{Softmax}(z_i) = \frac{e^{z_i}}{\sum_{j=1}^{C} e^{z_j}}
```

Trong đó:

- `z_i`: logit của class `i`.
- `C`: tổng số class cần phân biệt.
- `Softmax(z_i)`: xác suất của class `i`.

Sau Softmax, tổng xác suất của tất cả class bằng 1:

```math
\sum_{i=1}^{C} \operatorname{Softmax}(z_i) = 1
```

Ví dụ:

```text
ŷ = [0.08, 0.72, 0.15, 0.05]
```

Nghĩa là mô hình dự đoán:

- class 0 (`0`): 8%
- class 1 (`p15`): 72%
- class 2 (`m15`): 15%
- class 3 (`p30`): 5%

Nếu nhãn thật là class `p15`, mô hình đang dự đoán khá tốt vì class đúng có xác suất cao nhất.

---

#### 6.5. Công thức Cross Entropy

Công thức Cross Entropy:

```math
\mathrm{CE} = -\sum_{i=1}^{C} y_i \log(\hat{y}_i)
```

Trong đó:

- `C`: số class.
- `y_i`: giá trị nhãn thật tại class `i`.
- `ŷ_i`: xác suất mô hình dự đoán cho class `i`.

Vì `y` là dãy nhãn chỉ có một vị trí đúng bằng `1`, nên Cross Entropy thực chất tập trung vào xác suất mà mô hình gán cho class đúng.

Ví dụ:

```text
y = [0, 1, 0, 0]
```

```text
ŷ = [0.08, 0.72, 0.15, 0.05]
```

Khi đó:

```math
\mathrm{CE} = -\log(0.7)
```

Nếu mô hình dự đoán class đúng với xác suất càng cao, loss càng nhỏ. Nếu mô hình gán xác suất thấp cho class đúng, loss càng lớn.

---

#### 6.6. Ý nghĩa của Cross Entropy

Cross Entropy khuyến khích mô hình gán xác suất cao cho class đúng và xác suất thấp cho các class sai.

Ví dụ nhãn thật là class `p15`.

Trường hợp mô hình dự đoán tốt:

```text
ŷ = [0.05, 0.90, 0.03, 0.02]
```

Loss nhỏ vì xác suất của class đúng `p15` là 0.90.

Trường hợp mô hình dự đoán chưa chắc chắn:

```text
ŷ = [0.25, 0.40, 0.20, 0.15]
```

Loss trung bình vì class đúng `p15` vẫn cao nhất nhưng xác suất chưa lớn.

Trường hợp mô hình dự đoán sai tự tin:

```text
ŷ = [0.80, 0.05, 0.10, 0.05]
```

Loss lớn vì class đúng `p15` chỉ được gán xác suất 0.05.

---

#### 6.7. Cross Entropy trong PyTorch

Trong PyTorch, hàm thường dùng là:

```python
torch.nn.CrossEntropyLoss()
```

Hàm này nhận input là logits, tức là output thô của mô hình, chưa qua Softmax.

Do đó, khi dùng `CrossEntropyLoss`, không nên tự thêm Softmax trước khi tính loss.

Cách dùng đúng:

```python
logits = model(images)
loss = criterion(logits, labels)
```

Không nên dùng:

```python
probs = softmax(model(images))
loss = criterion(probs, labels)
```

Lý do là `CrossEntropyLoss` đã xử lý phần tương đương với Softmax bên trong quá trình tính loss.

---

#### 6.8. So sánh BCE và CE

| Tiêu chí | Binary Cross Entropy | Cross Entropy |
|---|---|---|
| Dạng bài toán | Binary / Multi-label | Multi-class |
| Số class | 2 hoặc nhiều nhãn độc lập | Nhiều class loại trừ nhau |
| Một mẫu có nhiều nhãn đúng không? | Có thể có | Không |
| Activation thường đi kèm | Sigmoid | Softmax |
| Output | Xác suất độc lập từng nhãn | Phân phối xác suất trên các class |
| Ví dụ | Ảnh có Leanbot hay không | Leanbot thuộc góc nào |

---

### 7. Bài toán phân loại 24 class góc của Leanbot

Trong bài toán Leanbot, mục tiêu là phân loại hướng/góc của robot từ ảnh đầu vào. Nếu ta chia hướng quay thành 24 class, mỗi class sẽ được biểu diễn bằng tên nhãn theo quy ước `p/m`.

Các class liền kề nhau cách nhau 15 độ, nhưng trong báo cáo này tên class sẽ được viết theo dạng `0`, `p15`, `m15`, `p30`, ...

Ta có thể định nghĩa 24 class như sau. Ở đây, tên class được giữ đúng theo cách bạn đặt trong dataset, tức là dùng ký hiệu `p` và `m` thay vì đổi sang biểu diễn theo số độ:

| ID | Tên class |
|---:|---|
| 0 | `0` |
| 1 | `p15` |
| 2 | `m15` |
| 3 | `p30` |
| 4 | `m30` |
| 5 | `p45` |
| 6 | `m45` |
| 7 | `p60` |
| 8 | `m60` |
| 9 | `p75` |
| 10 | `m75` |
| 11 | `p90` |
| 12 | `m90` |
| 13 | `p105` |
| 14 | `m105` |
| 15 | `p120` |
| 16 | `m120` |
| 17 | `p135` |
| 18 | `m135` |
| 19 | `p150` |
| 20 | `m150` |
| 21 | `p165` |
| 22 | `180` |
| 23 | `p195` |

Với cách đặt tên này, mỗi ảnh Leanbot chỉ thuộc về một class duy nhất. Do đó, đây là bài toán multi-class classification.

Đầu vào của bài toán:

```math
x = \text{image}
```

Đầu ra mong muốn:

```math
y \in \{0, 1, 2, \ldots, 23\}
```

Mô hình sẽ dự đoán vector logits có 24 phần tử:

```math
z = [z_0, z_1, z_2, \ldots, z_{23}]
```

Sau Softmax, ta thu được phân phối xác suất:

```math
\hat{y} = [p_0, p_1, p_2, \ldots, p_{23}]
```

Trong đó:

```math
\sum_{i=0}^{23} p_i = 1
```

Class dự đoán cuối cùng là class có xác suất lớn nhất:

```math
\mathrm{class}_{\mathrm{pred}} = \arg\max_i (p_i)
```

Vì đây là bài toán multi-class, loss function phù hợp là Cross Entropy.

---

#### 7.1. Vấn đề đặc biệt của bài toán góc

Tuy nhiên, bài toán góc có một đặc điểm khác với bài toán classification thông thường.

Trong nhiều bài toán classification thông thường, các class chỉ là các nhãn rời rạc và không có quan hệ hình học rõ ràng.

Nhưng với bài toán góc, các class có quan hệ hình học với nhau. Ví dụ:

- Dự đoán `p45` thành `p60` là sai nhẹ.
- Dự đoán `p45` thành `180` là sai nặng.
- Dự đoán `0` thành `m15` thực ra chỉ sai 15 độ nếu xét theo vòng tròn.

Trong khi đó, Cross Entropy cơ bản chỉ biết class đúng và class sai. Nó không tự hiểu rằng class liền kề về mặt góc là sai ít hơn class ở xa.

Ví dụ nhãn thật là `p45`:

| Dự đoán | Sai số góc | Theo CE cơ bản |
|---:|---:|---|
| `p60` | `15 độ` | Sai |
| `180` | `135 độ` | Sai |
| `m15` | `60 độ` | Sai |

CE cơ bản đều coi các class sai là sai, chưa phản ánh trực tiếp mức độ sai lệch góc.

Vì vậy, với bài toán Leanbot 24 class, có thể bắt đầu bằng Cross Entropy chuẩn để tạo baseline. Sau đó, nếu cần tối ưu tốt hơn, có thể cân nhắc các hướng cải tiến như:

1. Label smoothing để giảm overconfidence.
2. Soft-label Cross Entropy theo góc lân cận.
3. Focal Cross Entropy để tập trung vào các ảnh khó phân biệt.
4. Angle-aware loss để phạt mạnh hơn khi dự đoán sai xa về góc.

---

### 8. YOLO Classification
Các nguồn tham khảo: 

- Ultralytics `ClassificationTrainer` và hướng dẫn custom trainer:
  https://docs.ultralytics.com/reference/models/yolo/classify/train/
  https://docs.ultralytics.com/guides/custom-trainer/
- Ultralytics `ClassificationModel.init_criterion()` và source `v8ClassificationLoss`:
  https://docs.ultralytics.com/reference/nn/tasks/
  https://github.com/ultralytics/ultralytics/blob/main/ultralytics/utils/loss.py
- PyTorch `torch.nn.functional.cross_entropy`:
  https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.cross_entropy.ht
  
#### 8.1. Định nghĩa

YOLO thường được biết đến nhiều trong bài toán object detection, tức là phát hiện vị trí và class của đối tượng trong ảnh. Tuy nhiên, các phiên bản Ultralytics YOLO cũng hỗ trợ tác vụ image classification.

Trong bài toán YOLO classification, mô hình nhận vào toàn bộ ảnh và đưa ra một nhãn class cho ảnh đó.

Khác với object detection:

- Object detection: dự đoán bbox, class và confidence cho từng object.
- Image classification: dự đoán class của toàn bộ ảnh.

Với bài toán Leanbot 24 class góc, nếu ảnh đầu vào đã được crop hoặc xử lý sao cho trọng tâm là Leanbot, thì YOLO classification có thể được dùng để phân loại ảnh vào một trong 24 class góc như `0`, `p15`, `m15`, ...

Đầu vào:

```text
image
```

Đầu ra:

```math
\mathrm{class} \in \{0, 1, 2, \ldots, 23\}
```

Mô hình YOLO classification thường có phần backbone để trích xuất đặc trưng ảnh, sau đó là classification head để đưa ra logits cho các class.

Với 24 class, classification head sẽ sinh ra vector 24 giá trị:

```math
z = [z_0, z_1, \ldots, z_{23}]
```

Sau đó, Cross Entropy được dùng để tính loss giữa logits và nhãn thật.

---

#### 8.2. Loss function trong YOLO Classification

Với YOLO classification của Ultralytics, loss mặc định cho classification task là Cross Entropy.

Về mặt bản chất, nếu batch có `N` ảnh và số class là `C = 24`, output của mô hình có dạng:

```math
\mathrm{logits} \in \mathbb{R}^{N \times 24}
```

Nhãn thật có dạng:

```math
\mathrm{labels} \in \{0, 1, 2, \ldots, 23\}
```

Loss được tính bằng Cross Entropy:

```math
\mathrm{Loss} = \mathrm{CE}(\mathrm{logits}, \mathrm{labels})
```

Trong PyTorch, biểu diễn tương ứng là:

```python
loss = F.cross_entropy(preds, batch["cls"], reduction="mean")
```

Điều này có nghĩa là:

- `preds`: logits đầu ra của model.
- `batch["cls"]`: nhãn class thật.
- `F.cross_entropy`: hàm Cross Entropy.
- `reduction="mean"`: lấy trung bình loss trên batch.

Trong source code của Ultralytics, `ClassificationModel.init_criterion()` khởi tạo `v8ClassificationLoss()`, và phần `v8ClassificationLoss` cho bài toán classification thực chất cũng gọi `F.cross_entropy(preds, batch["cls"], reduction="mean")`.

Với bài toán Leanbot 24 class, Cross Entropy là lựa chọn mặc định hợp lý vì mỗi ảnh chỉ thuộc một class góc.

---

#### 8.3. Các cách thay đổi Cross Entropy trong YOLO classification cho bài toán 24 class Leanbot

Trong Ultralytics YOLO classification, phần loss mặc định cho nhánh phân loại về bản chất là:

```python
loss = F.cross_entropy(preds, batch["cls"], reduction="mean")
```

Phần loss classification của Ultralytics YOLO có thể chỉnh sửa được vì toàn bộ pipeline huấn luyện được xây dựng trên `ultralytics`, còn phần tính loss và tensor operations được thực hiện bằng `torch`. Ở mức mặc định, `ClassificationModel.init_criterion()` khởi tạo `v8ClassificationLoss()`, và trong source code của `v8ClassificationLoss`, loss cho classification được tính bằng `F.cross_entropy(preds, batch["cls"], reduction="mean")`. Điều này cho thấy Cross Entropy trong YOLO classification không phải là một khối đóng cố định, mà là một thành phần có thể điều chỉnh hoặc thay thế khi cần.

Về mặt triển khai, có thể can thiệp theo ba mức. Mức thứ nhất là giữ nguyên cấu trúc Cross Entropy nhưng thay đổi tham số, ví dụ `label_smoothing`. Mức thứ hai là thay trực tiếp lời gọi `F.cross_entropy(...)` bằng một hàm loss mới như Focal Cross Entropy hoặc CE kết hợp sai số góc. Mức thứ ba là subclass trainer hoặc model của Ultralytics để gắn custom loss vào quy trình `model.train(...)`. Với bài toán Leanbot 24 class, dataset hiện đã cân bằng, nên trọng tâm của việc chỉnh sửa loss không nằm ở xử lý lệch phân bố class mà nằm ở việc làm cho Cross Entropy phản ánh tốt hơn độ khó phân biệt giữa các class gần nhau như `0`, `p15`, `m15`, `p45`, `p60`.

Các hướng chỉnh sửa sẽ được xét trong phần này gồm:

1. Label smoothing
2. Soft-label Cross Entropy theo góc lân cận
3. Focal Cross Entropy
4. Cross Entropy kết hợp sai số góc


##### 8.3.1. Label smoothing

Label smoothing là cách thay đổi Cross Entropy nhẹ nhất. Thay vì dùng nhãn one-hot tuyệt đối, ta làm mềm nhãn thật để mô hình bớt học theo hướng quá tự tin.

Ví dụ, nếu ảnh thuộc class `p45`, nhãn one-hot chuẩn là:

```text
[0, 0, 0, 1, 0, ..., 0]
```

Theo ý tưởng label smoothing, nhãn sẽ không còn tuyệt đối 1 và 0 nữa, mà trở thành một phân bố mềm hơn, ví dụ:

```text
[0.002, 0.002, 0.002, 0.950, 0.002, ..., 0.002]
```

Cách này không đưa trực tiếp thông tin về góc lân cận vào target, nhưng giúp mô hình bớt overconfident khi ranh giới giữa các class như `p30`, `p45`, `p60` khá giống nhau.

Trong PyTorch có thể dùng trực tiếp:

```python
criterion = torch.nn.CrossEntropyLoss(label_smoothing=0.05)
loss = criterion(logits, labels)
```

Nếu chỉ muốn thay đổi nhẹ loss mặc định của YOLO classification, đây là lựa chọn đơn giản nhất.

---

##### 8.3.2. Soft-label Cross Entropy theo góc lân cận

Với bài toán Leanbot, class góc gần nhau không nên bị coi là sai giống hệt các class ở rất xa. Vì vậy, thay vì one-hot target, có thể dùng soft label để phân bố một phần xác suất cho các góc lân cận.

Ví dụ, nếu nhãn thật là `p45`, có thể dùng target:

| Class lân cận | Target |
|---:|---:|
| `p30` | 0.10 |
| `p45` | 0.80 |
| `p60` | 0.10 |

Với class `0`, cũng cần tính tính chu kỳ của góc:

- `0` gần `p15`
- `0` cũng gần `m15`

Dù tên class được viết theo dạng `p/m`, khi quy đổi sang giá trị góc để tính sai số theo vòng tròn vẫn có thể dùng công thức:

```math
d(\theta_1, \theta_2) = \min\left( |\theta_1 - \theta_2|,\ 360^\circ - |\theta_1 - \theta_2| \right)
```

Sau đó có thể xây target mềm bằng phân phối Gaussian:

```math
\text{target}_i =
\frac{
\exp\left( -\frac{d(\theta_i, \theta_{\text{true}})^2}{2\sigma^2} \right)
}{
\sum_j \exp\left( -\frac{d(\theta_j, \theta_{\text{true}})^2}{2\sigma^2} \right)
}
```

Theo tài liệu chính thức của PyTorch, `F.cross_entropy` có thể nhận `target` là class index hoặc class probabilities. Vì vậy, với soft-label CE, ta có thể dùng trực tiếp vector target mềm kích thước `24` cho mỗi ảnh:

```python
loss = F.cross_entropy(logits, targets, reduction="mean")
```

Đây là cách thay đổi Cross Entropy phù hợp nhất nếu muốn giữ bản chất CE nhưng đưa quan hệ hình học của 24 góc Leanbot vào loss.

---

##### 8.3.3. Focal Cross Entropy

Focal Cross Entropy là một biến thể của Cross Entropy nhằm giảm ảnh hưởng của các mẫu dễ và tăng tập trung vào các mẫu khó. Với dataset Leanbot đã cân bằng, vai trò chính của Focal CE không phải là cân bằng class, mà là dồn gradient vào những ảnh khó phân biệt.

Trong bài toán này, các mẫu khó thường là:

- `0` so với `p15` hoặc `m15`
- `p45` so với `p30` hoặc `p60`
- các class ở vùng phía sau như `p165`, `180`, `p195`

Công thức:

```math
\mathrm{FL} = -\alpha (1-p_t)^{\gamma} \log(p_t)
```

Trong đó:

- `p_t`: xác suất mô hình gán cho class đúng
- `gamma`: mức độ tập trung vào mẫu khó
- `alpha`: hệ số cân bằng

Ý nghĩa của công thức:

- Nếu mô hình đã đoán đúng và rất tự tin, `p_t` lớn, nên `(1 - p_t)^gamma` rất nhỏ và loss của mẫu đó bị giảm đi mạnh.
- Nếu mô hình còn nhầm hoặc chưa tự tin, `p_t` nhỏ, nên loss vẫn lớn và gradient vẫn tập trung vào mẫu đó.

Với dataset đã cân bằng, có thể đặt `alpha = 1.0` hoặc bỏ hẳn thành phần này. Khi đó Focal CE chủ yếu khác CE ở hệ số `(1 - p_t)^gamma`.

Ví dụ cài đặt bằng PyTorch:

```python
import torch
import torch.nn.functional as F

def focal_ce_loss(logits, labels, gamma=2.0, alpha=1.0):
    ce = F.cross_entropy(logits, labels, reduction="none")
    pt = torch.exp(-ce)
    loss = alpha * (1 - pt) ** gamma * ce
    return loss.mean()
```

Nếu dùng trong YOLO classification, ta thay:

```python
F.cross_entropy(preds, batch["cls"], reduction="mean")
```

bằng:

```python
focal_ce_loss(preds, batch["cls"], gamma=2.0, alpha=1.0)
```

Focal CE phù hợp khi mô hình đã học khá tốt phần lớn ảnh Leanbot, nhưng vẫn nhầm dai dẳng ở các cặp góc lân cận.

---

##### 8.3.4. Cross Entropy kết hợp sai số góc

Một hướng khác là vẫn giữ Cross Entropy làm loss chính, sau đó cộng thêm một thành phần phản ánh sai số góc:

```math
\mathrm{Loss} = \mathrm{CE} + \lambda \cdot \mathrm{AngleError}
```

Trong đó:

- `CE` giữ vai trò phân loại 24 class
- `AngleError` phạt mạnh hơn khi dự đoán sai xa về mặt góc
- `lambda` điều chỉnh mức độ ảnh hưởng của phần sai số góc

Ý tưởng này đặc biệt phù hợp với Leanbot vì nhầm từ `0` sang `p15` và nhầm từ `0` sang `180` rõ ràng không nên bị xem là cùng một mức lỗi.

Một cách tính đơn giản là lấy class dự đoán từ `argmax`, đổi class đó về góc rồi tính khoảng cách vòng tròn với góc thật. Một cách tốt hơn là tính sai số từ toàn bộ phân phối xác suất dự đoán để giữ thông tin mềm của logits.

---

##### 8.3.5. Cách tích hợp vào YOLO classification

Nếu chỉ dùng Cross Entropy chuẩn hoặc Cross Entropy với `label_smoothing`, phần thay đổi tương đối gọn vì vẫn giữ target dạng class index.

Nếu muốn dùng:

- soft-label Cross Entropy
- Focal Cross Entropy
- CE + AngleError

thì cần can thiệp vào phần trainer/loss để thay thế loss classification mặc định. Ý tưởng chung là:

```python
# loss mặc định
loss = F.cross_entropy(preds, batch["cls"], reduction="mean")

# loss đã chỉnh sửa
loss = custom_cls_loss(preds, batch["cls"])
```

Với soft-label CE, `custom_cls_loss` cần tự xây `targets` mềm từ nhãn góc thật. Với Focal CE, `custom_cls_loss` nhận trực tiếp `preds` và `batch["cls"]`. Với CE + AngleError, `custom_cls_loss` cần thêm bảng ánh xạ `class -> angle` cho đủ 24 class Leanbot.

Tóm lại, nếu xét riêng trong YOLO classification cho bài toán 24 class góc Leanbot:

- `Label smoothing` là cách sửa CE đơn giản nhất.
- `Soft-label CE` là cách đưa trực tiếp quan hệ góc lân cận vào target.
- `Focal CE` là cách làm CE tập trung mạnh hơn vào các ảnh khó phân biệt.
- `CE + AngleError` là cách giữ CE nhưng bổ sung ý nghĩa hình học của góc.

## B. Khó khăn

## C. Công việc tiếp theo
