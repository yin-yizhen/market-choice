# 店铺选址评估网页

这是一个中国大陆店铺选址评估第一版原型。用户搜索并选择点位，填写开店信息和财务成本，后端拉取高德 POI，计算财务与调研评分，并用大模型生成中文选址报告。

## 功能

- 地图工作台：搜索位置、选择候选点、显示 500m / 1km / 3km 圈层。
- 开店信息：目标业务、客单价、面积、员工、营业时段、差异化；目标客户由系统根据地址、POI、业态和商圈画像推断。
- 财务测算：用户只填写月租金和其余投资总计；物业、人工、水电、原材料、平台抽佣、营销、证照、预计月营收和毛利率由系统估算。
- POI 分析：按三圈层分页统计竞品、互补业态和主要类别，并标记是否被截断。
- 报告输出：综合得分、15 项评分、保本营业额、保本日单量、坪效、人效、最坏支撑月数、风险因素和预测报告。

## 数据边界

第一版真实接入高德地理编码和周边 POI。POI 会分页抓取，并在达到分页上限时标记 `truncated=true`。人流、消费能力、未来规划、夜间人气、周末人气、线上热度等为规则估算和 AI 研判。房价、城市更新、外卖价格、政策细则尚未接入真实数据源。

财务测算中，其余投资总计按 70% 开办成本、30% 备用资金拆分；一次性开办成本和可用备用金分开展示。“最坏情况可支撑月数”只用可用备用金除以月固定现金支出，不把装修、设备、转让费、押金视为可续命现金。未填写的营收、毛利和细项成本会在报告数据说明中标注为系统估算。

## 环境变量

复制 `.env.example` 到项目根目录 `.env`，并按需配置：

```bash
AMAP_WEB_SERVICE_KEY=your-amap-web-service-key
LLM_API_KEY=your-openai-compatible-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
FRONTEND_ORIGIN=http://localhost:5173
```

`AMAP_WEB_SERVICE_KEY` 给后端查询地理编码和 POI 使用。`LLM_*` 给后端生成 AI 报告使用。

前端还需要在 `frontend/.env` 中配置浏览器地图 key：

```bash
VITE_AMAP_JS_API_KEY=your-amap-js-api-key
```

不配置 `frontend/.env` 时，前端会显示可演示的圈层地图，但不会加载真实高德 JS 地图。

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
