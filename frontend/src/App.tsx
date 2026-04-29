import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, BarChart3, Loader2, MapPin, Search, WalletCards } from 'lucide-react';

import { analyzeLocation, geocode } from './api';
import type { AnalysisResponse, BusinessInput, FinancialInput, LocationCandidate } from './types';
import './styles.css';

const defaultBusiness: BusinessInput = {
  business_type: '咖啡店',
  average_ticket: 32,
  store_area: 80,
  employee_count: 4,
  target_customer: '周边白领、社区居民、周末逛街人群',
  opening_hours: '08:00-22:00',
  differentiation: '精品咖啡、轻食、外带效率高',
};

const defaultFinancial: FinancialInput = {
  monthly_rent: 28000,
  property_fee: 1800,
  transfer_fee: 80000,
  deposit: 56000,
  renovation_cost: 160000,
  equipment_cost: 90000,
  labor_cost: 42000,
  utilities_cost: 6000,
  raw_material_cost: 52000,
  platform_commission: 8000,
  marketing_cost: 10000,
  license_cost: 8000,
  working_capital: 90000,
  expected_monthly_revenue: 180000,
  gross_margin: 0.58,
};

const demoLocation: LocationCandidate = {
  name: '上海市静安区南京西路示例点位',
  address: '上海市静安区南京西路',
  city: '上海',
  district: '静安区',
  latitude: 31.2304,
  longitude: 121.4737,
};

type LoadingStep = 'idle' | 'poi' | 'finance' | 'report';

export default function App() {
  const [keyword, setKeyword] = useState('');
  const [city, setCity] = useState('上海');
  const [candidates, setCandidates] = useState<LocationCandidate[]>([]);
  const [selected, setSelected] = useState<LocationCandidate | null>(null);
  const [business, setBusiness] = useState<BusinessInput>(defaultBusiness);
  const [financial, setFinancial] = useState<FinancialInput>(defaultFinancial);
  const [report, setReport] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState('');
  const [loadingStep, setLoadingStep] = useState<LoadingStep>('idle');

  const loadingLabel = useMemo(() => {
    if (loadingStep === 'poi') return '正在分析 POI';
    if (loadingStep === 'finance') return '正在测算财务';
    if (loadingStep === 'report') return '正在生成报告';
    return '';
  }, [loadingStep]);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    if (!keyword.trim()) {
      setError('请输入要搜索的位置');
      return;
    }
    setError('');
    setCandidates([]);
    const result = await geocode(keyword.trim(), city.trim());
    setCandidates(result);
    if (result.length === 0) setError('没有找到候选位置，请换一个关键词');
  }

  async function handleAnalyze() {
    if (!selected) {
      setError('请先搜索并选择一个位置');
      return;
    }
    setError('');
    setReport(null);
    setLoadingStep('poi');
    try {
      window.setTimeout(() => setLoadingStep('finance'), 120);
      window.setTimeout(() => setLoadingStep('report'), 240);
      const result = await analyzeLocation({ location: selected, business, financial });
      setReport(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '分析失败');
    } finally {
      setLoadingStep('idle');
    }
  }

  return (
    <main className="app-shell">
      <section className="map-panel" aria-label="地图选址工作台">
        <div className="toolbar">
          <div>
            <h1>店铺选址评估</h1>
            <p>搜索点位，填写经营与成本假设，生成三圈层调研报告。</p>
          </div>
          <span className="data-badge">高德 POI + AI 研判</span>
        </div>

        <form className="search-row" onSubmit={handleSearch}>
          <label>
            搜索位置
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="例如：上海 南京西路" />
          </label>
          <label>
            城市
            <input value={city} onChange={(event) => setCity(event.target.value)} placeholder="上海" />
          </label>
          <button type="submit">
            <Search size={17} />
            搜索
          </button>
          <button className="ghost-action" type="button" onClick={() => setSelected(demoLocation)}>
            使用示例点位
          </button>
        </form>

        {candidates.length > 0 && (
          <div className="candidate-list">
            {candidates.map((candidate) => (
              <button key={`${candidate.longitude}-${candidate.latitude}`} type="button" onClick={() => setSelected(candidate)}>
                <MapPin size={16} />
                选择 {candidate.name}
                <span>{candidate.district || candidate.city}</span>
              </button>
            ))}
          </div>
        )}

        <MapCanvas selected={selected} />
      </section>

      <aside className="control-panel">
        {error && (
          <div className="error-banner" role="alert">
            <AlertTriangle size={17} />
            {error}
          </div>
        )}

        <BusinessForm business={business} onChange={setBusiness} />
        <FinancialForm financial={financial} onChange={setFinancial} />

        <button className="primary-action" type="button" onClick={handleAnalyze} disabled={loadingStep !== 'idle'}>
          {loadingStep !== 'idle' ? <Loader2 className="spin" size={18} /> : <BarChart3 size={18} />}
          {loadingStep === 'idle' ? '生成选址报告' : loadingLabel}
        </button>

        {report && <ReportPanel report={report} />}
      </aside>
    </main>
  );
}

function MapCanvas({ selected }: { selected: LocationCandidate | null }) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const [amapReady, setAmapReady] = useState(false);

  useEffect(() => {
    const key = import.meta.env.VITE_AMAP_JS_API_KEY;
    if (!key || window.AMap) {
      setAmapReady(Boolean(window.AMap));
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>('script[data-amap-loader="true"]');
    if (existing) {
      existing.addEventListener('load', () => setAmapReady(Boolean(window.AMap)), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.dataset.amapLoader = 'true';
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`;
    script.async = true;
    script.onload = () => setAmapReady(Boolean(window.AMap));
    document.head.appendChild(script);
  }, []);

  useEffect(() => {
    if (!selected || !amapReady || !mapRef.current || !window.AMap) return;
    const AMap = window.AMap;
    const center: [number, number] = [selected.longitude, selected.latitude];
    const map = new AMap.Map(mapRef.current, {
      zoom: 15,
      center,
      resizeEnable: true,
    });
    new AMap.Marker({ position: center, map });
    [500, 1000, 3000].forEach((radius) => {
      new AMap.Circle({
        center,
        radius,
        map,
        strokeColor: radius === 500 ? '#a85d24' : radius === 1000 ? '#1c6a94' : '#1f6f4a',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillOpacity: 0.08,
        fillColor: '#1f6f4a',
      });
    });
    return () => map.destroy();
  }, [selected, amapReady]);

  return (
    <div className="map-canvas">
      <div ref={mapRef} className={amapReady && selected ? 'amap-layer is-visible' : 'amap-layer'} />
      <div className="grid-layer" />
      {selected ? (
        <div className="map-focus">
          <div className="ring ring-3000"><span>3km</span></div>
          <div className="ring ring-1000"><span>1km</span></div>
          <div className="ring ring-500"><span>500m</span></div>
          <div className="pin">
            <MapPin size={22} />
          </div>
          <div className="location-card">
            <strong>{selected.name}</strong>
            <span>{selected.latitude.toFixed(4)}, {selected.longitude.toFixed(4)}</span>
          </div>
        </div>
      ) : (
        <div className="empty-map">
          <MapPin size={28} />
          <strong>搜索并选择一个点位</strong>
          <span>选择后会显示 500m、1km、3km 三个评估圈层。</span>
        </div>
      )}
    </div>
  );
}

function BusinessForm({ business, onChange }: { business: BusinessInput; onChange: (value: BusinessInput) => void }) {
  return (
    <section className="form-section">
      <h2>开店信息</h2>
      <div className="form-grid">
        <TextField label="目标业务" value={business.business_type} onChange={(value) => onChange({ ...business, business_type: value })} />
        <NumberField label="客单价" value={business.average_ticket} onChange={(value) => onChange({ ...business, average_ticket: value })} />
        <NumberField label="店铺面积" value={business.store_area} onChange={(value) => onChange({ ...business, store_area: value })} />
        <NumberField label="员工数" value={business.employee_count} onChange={(value) => onChange({ ...business, employee_count: value })} />
        <TextField label="营业时段" value={business.opening_hours} onChange={(value) => onChange({ ...business, opening_hours: value })} />
        <TextField label="目标客户" value={business.target_customer} onChange={(value) => onChange({ ...business, target_customer: value })} />
      </div>
      <label className="wide-field">
        差异化
        <textarea value={business.differentiation} onChange={(event) => onChange({ ...business, differentiation: event.target.value })} />
      </label>
    </section>
  );
}

function FinancialForm({ financial, onChange }: { financial: FinancialInput; onChange: (value: FinancialInput) => void }) {
  const set = (key: keyof FinancialInput, value: number) => onChange({ ...financial, [key]: value });
  return (
    <section className="form-section">
      <h2><WalletCards size={18} /> 财务测算</h2>
      <div className="form-grid">
        <NumberField label="月租金" value={financial.monthly_rent} onChange={(value) => set('monthly_rent', value)} />
        <NumberField label="物业费" value={financial.property_fee} onChange={(value) => set('property_fee', value)} />
        <NumberField label="转让费" value={financial.transfer_fee} onChange={(value) => set('transfer_fee', value)} />
        <NumberField label="押金" value={financial.deposit} onChange={(value) => set('deposit', value)} />
        <NumberField label="装修成本" value={financial.renovation_cost} onChange={(value) => set('renovation_cost', value)} />
        <NumberField label="设备成本" value={financial.equipment_cost} onChange={(value) => set('equipment_cost', value)} />
        <NumberField label="人工成本" value={financial.labor_cost} onChange={(value) => set('labor_cost', value)} />
        <NumberField label="水电燃气" value={financial.utilities_cost} onChange={(value) => set('utilities_cost', value)} />
        <NumberField label="原材料成本" value={financial.raw_material_cost} onChange={(value) => set('raw_material_cost', value)} />
        <NumberField label="平台抽佣" value={financial.platform_commission} onChange={(value) => set('platform_commission', value)} />
        <NumberField label="营销费用" value={financial.marketing_cost} onChange={(value) => set('marketing_cost', value)} />
        <NumberField label="证照费用" value={financial.license_cost} onChange={(value) => set('license_cost', value)} />
        <NumberField label="备用资金" value={financial.working_capital} onChange={(value) => set('working_capital', value)} />
        <NumberField label="预计月营收" value={financial.expected_monthly_revenue} onChange={(value) => set('expected_monthly_revenue', value)} />
        <NumberField label="毛利率" value={financial.gross_margin} step={0.01} onChange={(value) => set('gross_margin', value)} />
      </div>
    </section>
  );
}

function ReportPanel({ report }: { report: AnalysisResponse }) {
  return (
    <section className="report-panel">
      <div className="score-card">
        <span>综合得分 {report.scoring.overall_score}</span>
        <small>{report.report.source === 'llm' ? 'AI 报告' : '规则降级报告'}</small>
      </div>

      <div className="report-grid">
        <Metric label="保本营业额" value={`${report.financials.break_even_revenue ?? 0} 元/月`} />
        <Metric label="最坏支撑" value={`${report.financials.survival_months_worst_case ?? 0} 个月`} />
        <Metric label="现金压力" value={`${report.financials.cash_pressure_level ?? '-'}`} />
      </div>

      <h3>三圈层 POI</h3>
      <div className="ring-summary">
        {report.poi_rings.map((ring) => (
          <div key={ring.radius}>
            <strong>{ring.radius}m</strong>
            <span>{ring.total} POI</span>
            <span>竞品 {ring.competitor_count}</span>
            <span>{ring.truncated ? '已截断' : `互补 ${ring.complementary_count}`}</span>
          </div>
        ))}
      </div>

      {report.scoring.business_metrics && (
        <>
          <h3>经营测算</h3>
          <div className="report-grid">
            <Metric label="保本日单量" value={`${report.scoring.business_metrics.break_even_daily_orders ?? 0} 单`} />
            <Metric label="月坪效" value={`${report.scoring.business_metrics.monthly_revenue_per_sqm ?? '-'} 元/㎡`} />
            <Metric label="人效" value={`${report.scoring.business_metrics.monthly_revenue_per_employee ?? '-'} 元/人`} />
          </div>
        </>
      )}

      <h3>调研评分</h3>
      <div className="score-list">
        {Object.entries(report.scoring.scores).map(([name, score]) => (
          <div key={name}>
            <span>{name}</span>
            <meter min="0" max="100" value={score} />
            <strong>{score}</strong>
          </div>
        ))}
      </div>

      <h3>风险因素</h3>
      <ul className="risk-list">
        {report.scoring.risk_factors.map((risk) => <li key={risk}>{risk}</li>)}
      </ul>

      <h3>预测报告</h3>
      <div className="markdown-report">
        {report.report.markdown.split('\n').map((line, index) => (
          <p key={`${line}-${index}`}>{line.replace(/^#+\s*/, '') || '\u00A0'}</p>
        ))}
      </div>

      <h3>数据说明</h3>
      <ul className="note-list">
        {report.data_notes.map((note) => <li key={note}>{note}</li>)}
      </ul>

      {report.scoring.verification_required && (
        <>
          <h3>待线下核验</h3>
          <ul className="note-list">
            {report.scoring.verification_required.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberField({
  label,
  value,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        min="0"
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
