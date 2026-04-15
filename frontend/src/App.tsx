import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingDown, Server, AlertTriangle, DollarSign } from 'lucide-react'
import { api, Summary, AllocationItem, RecommendationsResponse, BillingResponse } from './api/client'

const COLORS = ['#00d4b1', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
const RISK_COLOR = { low: '#00d4b1', medium: '#f59e0b', high: '#ef4444' }

const s: Record<string, React.CSSProperties> = {
  app: { minHeight: '100vh', padding: '24px', maxWidth: '1400px', margin: '0 auto' },
  header: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px' },
  title: { fontSize: '24px', fontWeight: 700, color: '#f1f5f9' },
  subtitle: { fontSize: '14px', color: '#64748b' },
  grid4: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' },
  card: { background: '#1e2433', borderRadius: '12px', padding: '20px', border: '1px solid #2d3748' },
  cardTitle: { fontSize: '13px', color: '#94a3b8', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' },
  bigNum: { fontSize: '32px', fontWeight: 700, color: '#f1f5f9' },
  label: { fontSize: '12px', color: '#64748b', marginTop: '4px' },
  badge: (risk: string) => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: '999px', fontSize: '11px',
    background: (RISK_COLOR as any)[risk] + '22', color: (RISK_COLOR as any)[risk], fontWeight: 600,
  }),
  table: { width: '100%', borderCollapse: 'collapse' as const },
  th: { textAlign: 'left' as const, padding: '8px 12px', fontSize: '12px', color: '#64748b', borderBottom: '1px solid #2d3748' },
  td: { padding: '10px 12px', fontSize: '13px', borderBottom: '1px solid #1a2030' },
  tag: { display: 'inline-block', padding: '2px 8px', background: '#0f1928', borderRadius: '6px', fontSize: '12px', fontFamily: 'monospace' },
  loader: { textAlign: 'center' as const, color: '#64748b', padding: '60px' },
}

function KPI({ icon, title, value, sub }: { icon: React.ReactNode; title: string; value: string; sub: string }) {
  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={s.cardTitle}>{title}</div>
          <div style={s.bigNum}>{value}</div>
          <div style={s.label}>{sub}</div>
        </div>
        <div style={{ color: '#00d4b1', opacity: 0.7 }}>{icon}</div>
      </div>
    </div>
  )
}

export default function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [allocs, setAllocs] = useState<AllocationItem[]>([])
  const [recs, setRecs] = useState<RecommendationsResponse | null>(null)
  const [billing, setBilling] = useState<BillingResponse | null>(null)
  const [window_, setWindow] = useState('30d')
  const [tab, setTab] = useState<'overview' | 'namespaces' | 'recommendations' | 'billing'>('overview')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      api.summary(window_).then(setSummary),
      api.allocations(window_).then(r => setAllocs(r.items.slice(0, 15))),
      api.recommendations().then(setRecs),
      api.billing().then(setBilling),
    ]).finally(() => setLoading(false))
  }, [window_])

  const tabs = ['overview', 'namespaces', 'recommendations', 'billing'] as const
  const tabLabel: Record<typeof tabs[number], string> = {
    overview: 'Обзор', namespaces: 'Неймспейсы', recommendations: 'Рекомендации', billing: 'Биллинг YC',
  }

  return (
    <div style={s.app}>
      {/* Header */}
      <div style={s.header}>
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect width="32" height="32" rx="8" fill="#00d4b1" fillOpacity=".15"/>
          <path d="M8 22 L14 14 L19 18 L26 10" stroke="#00d4b1" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="26" cy="10" r="2.5" fill="#00d4b1"/>
        </svg>
        <div>
          <div style={s.title}>FinOps Dashboard</div>
          <div style={s.subtitle}>Yandex Cloud · Kubernetes Cost Intelligence</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
          {['7d', '30d', '90d'].map(w => (
            <button key={w} onClick={() => setWindow(w)} style={{
              padding: '6px 14px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              background: window_ === w ? '#00d4b1' : '#1e2433', color: window_ === w ? '#0f1117' : '#94a3b8',
              fontWeight: 600, fontSize: '13px',
            }}>{w}</button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', background: '#1e2433', borderRadius: '10px', padding: '4px', width: 'fit-content' }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: '8px 18px', borderRadius: '8px', border: 'none', cursor: 'pointer',
            background: tab === t ? '#2d3748' : 'transparent',
            color: tab === t ? '#f1f5f9' : '#64748b', fontSize: '14px', fontWeight: tab === t ? 600 : 400,
          }}>{tabLabel[t]}</button>
        ))}
      </div>

      {loading && <div style={s.loader}>Загрузка данных...</div>}

      {!loading && tab === 'overview' && (
        <>
          <div style={s.grid4}>
            <KPI icon={<DollarSign size={24}/>} title="Всего расходов" value={`₽ ${(summary?.total_cost ?? 0).toLocaleString('ru')}`} sub={`за ${window_}`}/>
            <KPI icon={<Server size={24}/>} title="Неймспейсов" value={String(summary?.namespace_count ?? 0)} sub="активных"/>
            <KPI icon={<TrendingDown size={24}/>} title="Потенциал экономии" value={`₽ ${(recs?.estimated_monthly_saving ?? 0).toLocaleString('ru')}`} sub="в месяц"/>
            <KPI icon={<AlertTriangle size={24}/>} title="Рекомендации" value={String(recs?.count ?? 0)} sub="активных"/>
          </div>

          <div style={s.grid2}>
            <div style={s.card}>
              <div style={s.cardTitle}>Топ неймспейсов по затратам (₽)</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={summary?.top_namespaces.map(n => ({ name: n.namespace.slice(0,14), cost: n.cost })) ?? []}>
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false}/>
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false}/>
                  <Tooltip contentStyle={{ background: '#1e2433', border: '1px solid #2d3748', borderRadius: '8px', color: '#f1f5f9' }}/>
                  <Bar dataKey="cost" radius={[4,4,0,0]}>
                    {(summary?.top_namespaces ?? []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={s.card}>
              <div style={s.cardTitle}>Фактические расходы YC (топ сервисы)</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={(billing?.by_service ?? []).slice(0,6).map(s => ({ name: s.service.slice(0,14), cost: s.cost }))} layout="vertical">
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false}/>
                  <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={100}/>
                  <Tooltip contentStyle={{ background: '#1e2433', border: '1px solid #2d3748', borderRadius: '8px', color: '#f1f5f9' }}/>
                  <Bar dataKey="cost" fill="#3b82f6" radius={[0,4,4,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {!loading && tab === 'namespaces' && (
        <div style={s.card}>
          <div style={{ ...s.cardTitle, marginBottom: '16px' }}>Расходы по неймспейсам — {window_}</div>
          <table style={s.table}>
            <thead>
              <tr>
                {['Namespace','CPU (₽)','RAM (₽)','PV (₽)','Итого (₽)'].map(h => <th key={h} style={s.th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {allocs.map(a => (
                <tr key={a.name}>
                  <td style={s.td}><span style={s.tag}>{a.name}</span></td>
                  <td style={s.td}>{a.cpu_cost.toFixed(2)}</td>
                  <td style={s.td}>{a.ram_cost.toFixed(2)}</td>
                  <td style={s.td}>{a.pv_cost.toFixed(2)}</td>
                  <td style={{ ...s.td, fontWeight: 600, color: '#00d4b1' }}>{a.total_cost.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === 'recommendations' && (
        <div style={s.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={s.cardTitle}>Рекомендации по оптимизации</div>
            <div style={{ color: '#00d4b1', fontSize: '14px', fontWeight: 600 }}>
              Потенциал: ₽ {(recs?.estimated_monthly_saving ?? 0).toLocaleString('ru')}/мес
            </div>
          </div>
          <table style={s.table}>
            <thead>
              <tr>{['Ресурс','Тип','Описание','Риск','Экономия (₽)'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {(recs?.items ?? []).map((r, i) => (
                <tr key={i}>
                  <td style={s.td}><span style={s.tag}>{r.resource}</span></td>
                  <td style={s.td}><span style={{ color: '#94a3b8' }}>{r.type}</span></td>
                  <td style={{ ...s.td, maxWidth: '300px', color: '#94a3b8', fontSize: '12px' }}>{r.description}</td>
                  <td style={s.td}><span style={s.badge(r.risk)}>{r.risk}</span></td>
                  <td style={{ ...s.td, fontWeight: 600, color: '#00d4b1' }}>
                    {r.potential_saving != null ? r.potential_saving.toFixed(2) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === 'billing' && (
        <div style={s.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={s.cardTitle}>Фактический биллинг YC — CSV из Object Storage</div>
            <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '20px' }}>
              ₽ {(billing?.total ?? 0).toLocaleString('ru')}
            </div>
          </div>
          <table style={s.table}>
            <thead><tr>{['Сервис YC','Расходы (₽)'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr></thead>
            <tbody>
              {(billing?.by_service ?? []).map((b, i) => (
                <tr key={i}>
                  <td style={s.td}>{b.service}</td>
                  <td style={{ ...s.td, fontWeight: 600 }}>₽ {b.cost.toLocaleString('ru')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
