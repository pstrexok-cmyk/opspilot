import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { translate, type Language } from './i18n'

type ChartDay = { date: string; cases_received: number; cases_resolved: number; backlog_end: number }

export default function TrendCharts({ data, language }: { data: ChartDay[]; language: Language }) {
  const number = new Intl.NumberFormat(language === 'en' ? 'en-GB' : 'ru-RU')
  const shortDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString(language === 'en' ? 'en-GB' : 'ru-RU', { day: 'numeric', month: 'short' })
  return <>
    <div className="chart-card">
      <div className="chart-heading"><div><h2>{translate(language, 'inflowChart')}</h2><p>{translate(language, 'weeklyFlows')}</p></div><span className="chart-unit">{translate(language, 'casesPerWeek')}</span></div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 8, left: -18, bottom: 0 }} barGap={3}>
            <CartesianGrid stroke="#edf1f3" vertical={false} />
            <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={35} tick={{ fill: '#81909c', fontSize: 11 }} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: '#81909c', fontSize: 11 }} />
            <Tooltip labelFormatter={(label) => shortDate(String(label))} formatter={(value, name) => [number.format(Number(value)), name === 'cases_received' ? translate(language, 'received') : translate(language, 'resolvedLegend')]} />
            <Bar dataKey="cases_received" name="cases_received" fill="#86b8b0" radius={[3, 3, 0, 0]} maxBarSize={14} />
            <Bar dataKey="cases_resolved" name="cases_resolved" fill="#247f78" radius={[3, 3, 0, 0]} maxBarSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="legend"><span><i className="legend-received" /> {translate(language, 'received')}</span><span><i className="legend-resolved" /> {translate(language, 'resolvedLegend')}</span></div>
    </div>

    <div className="chart-card">
      <div className="chart-heading"><div><h2>{translate(language, 'waitingChart')}</h2><p>{translate(language, 'waitingWeekly')}</p></div><span className="chart-unit">{translate(language, 'cases')}</span></div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#edf1f3" vertical={false} />
            <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={35} tick={{ fill: '#81909c', fontSize: 11 }} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: '#81909c', fontSize: 11 }} />
            <Tooltip labelFormatter={(label) => shortDate(String(label))} formatter={(value) => [number.format(Number(value)), translate(language, 'waitingChart')]} />
            <Line type="monotone" dataKey="backlog_end" name={translate(language, 'waitingChart')} stroke="#247f78" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#247f78' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-footnote">{translate(language, 'lastDayNote')}</div>
    </div>
  </>
}

