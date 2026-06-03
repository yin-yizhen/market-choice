# 店铺选址评估网页

这是一个中国大陆店铺选址评估原型。用户搜索并选择点位，填写开店信息和少量财务假设，后端拉取高德 POI，结合财务测算、联网调研证据和规则评分生成中文选址报告。

## 功能

- 地图工作台：搜索位置、选择候选点、显示 500m / 1km / 3km 圈层。
- 开店信息：目标业务、客单价、面积、员工、营业时段、差异化；目标客户由系统根据地址、POI、业态和商圈画像推断。
- 财务测算：用户只填写月租金和其余投资总计；其他成本、预计营收和毛利率由系统根据点位、业态、POI 和面积估算。
- POI 分析：按三圈层分页统计竞品、互补业态和主要类别，并标记是否被截断。
- 联网调研：默认支持阿里云百炼千问联网检索 Agent，也保留 Gemini Grounding 作为备用。
- 报告输出：综合得分、15 项评分、保本营业额、保本日单量、坪效、人效、最坏支撑月数、风险因素、联网证据和预测报告。

## 数据边界

第一版真实接入高德地理编码和周边 POI。人流、消费能力、未来规划、夜间人气、周末人气、线上热度等由联网公开资料、规则估算和 AI 研判共同形成。

财务测算中，其余投资总计按 70% 开办成本、30% 备用资金拆分；一次性开办成本和可用备用金分开展示。“最坏情况下可支撑月数”只用可用备用金除以月固定现金支出，不把装修、设备、转让费、押金视为可续命现金。

## 环境变量

后端读取项目根目录 `.env` 或 `backend/.env`。

```bash
AMAP_WEB_SERVICE_KEY=your-amap-web-service-key
LLM_API_KEY=your-openai-compatible-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
FRONTEND_ORIGIN=http://localhost:5173

RESEARCH_MODE=llm_grounding
LLM_GROUNDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_WEB_SEARCH_AGENT_ID=your-dashscope-web-search-agent-id
DASHSCOPE_WEB_SEARCH_AGENT_VERSION=beta
```

如果要切回 Gemini：

```bash
LLM_GROUNDING_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_GROUNDING_MODEL=gemini-2.5-pro
```

前端地图 key 放在 `frontend/.env`：

```bash
VITE_AMAP_JS_API_KEY=your-amap-js-api-key
VITE_AMAP_SECURITY_JS_CODE=your-amap-security-js-code
```

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

