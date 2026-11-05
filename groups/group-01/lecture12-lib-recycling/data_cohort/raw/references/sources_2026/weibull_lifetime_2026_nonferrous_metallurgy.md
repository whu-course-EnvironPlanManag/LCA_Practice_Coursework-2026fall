# 动力电池 Weibull 寿命参数（β=3.5，η=10 年）文献依据

- 文献题名：基于全球海关贸易数据的锂离子电池退役规模与资源化潜力预测
- 期刊：《有色金属(冶炼部分)》2026 年第 2 期
- 检索页：<https://mete.cbpt.cnki.net/portal/journal/portal/client/paper/d13ea0b741f47751c14b51ee61dfccd6>
- 摘要/预览页：<https://mete.cbpt.cnki.net/portal/journal/portal/client/paper/preview?cache=false&filePath=files%2Fmete%2Fhtmlfulltext%2Fpdf%2F2026%2F02%2F基于全球海关贸易数据的锂离子电池退役规模与资源化潜力预测.pdf>

## 摘要可引内容（英文摘要原文）

> Modified Weibull lifetime distribution parameters were applied for retirement evolution simulation, with shape parameter β=2.5 and characteristic lifetime η=4 years for consumer electronics batteries, and **β=3.5 and η=10 years for power batteries**. Weight correction coefficients of 0.75 and 0.85...

## 使用边界

1. 该文把 β=3.5、η=10 年用于**动力电池**退役演化，与本组 `material_parameters.csv` 的取值一致，可用于说明参数并非任意设定。
2. 本次只取得可公开访问的题录与英文摘要，**付费全文未下载**，因此无法核对作者使用的原始样本、年限区间与拟合方法；该文献只作为参数来源依据，不作为湖北本地校准。
3. 该文另给出消费电子电池 β=2.5、η=4 年及权重修正系数 0.75/0.85，本研究未采用，避免把不同电池类别参数混用。
4. 模型中 η=10、β=3.5 仍是**条件情景参数**：没有湖北逐车上牌与换包数据，不能据此声称已校准湖北退役曲线。
