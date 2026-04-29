# 店铺选址评估网页

这是一个中国大陆店铺选址评估第一版原型。用户搜索并选择点位，填写开店信息和财务成本，后端拉取高德 POI，计算财务与调研评分，并用大模型生成中文选址报告。

## 功能

- 地图工作台：搜索位置、选择候选点、显示 500m / 1km / 3km 圈层。
- 开店信息：目标业务、客单价、面积、员工、目标客户、营业时段、差异化。
- 财务测算：月租金、物业费、转让费、押金、装修、设备、人工、水电燃气、原材料、平台抽佣、营销、证照和备用资金。
- POI 分析：按三圈层统计竞品、互补业态和主要类别。
- 报告输出：综合得分、15 项评分、保本营业额、最坏支撑月数、风险因素和预测报告。

## 数据边界

第一版真实接入高德地理编码和周边 POI。人流、消费能力、未来规划、夜间人气、周末人气、线上热度等为规则估算和 AI 研判。房价、城市更新、外卖价格、政策细则尚未接入真实数据源。

## 环境变量

复制 `.env.example` 并按需配置：

```bash
AMAP_WEB_SERVICE_KEY=your-amap-web-service-key
LLM_API_KEY=your-openai-compatible-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
FRONTEND_ORIGIN=http://localhost:5173
VITE_AMAP_JS_API_KEY=your-amap-js-api-key
```

`AMAP_WEB_SERVICE_KEY` 给后端查询地理编码和 POI 使用。`VITE_AMAP_JS_API_KEY` 给浏览器显示真实高德地图使用；不配置时前端会显示可演示的圈层地图。

## 本地启动

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 测试

后端：

```bash
cd backend
python -m pytest -q
```

前端：

```bash
cd frontend
npm test
npm run build
```
