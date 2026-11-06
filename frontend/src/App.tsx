import { lazy, Suspense, useEffect, useMemo, useState, type FormEvent } from 'react'
import { translate, type Language } from './i18n'

const TrendCharts = lazy(() => import('./TrendCharts'))

type Dataset = {
  id: string
  name: string
  source_filename: string
  row_count: number
  date_from: string | null
  date_to: string | null
}

type MetricPoint = {
  date: string
  queue: string
  cases_received: number
  cases_resolved: number
  backlog_end: number
  avg_resolution_hours: number
  sla_breaches: number
  sla_breach_rate_pct: number | null
  reopened_cases: number
  csat_avg: number | null
}

type Metrics = {
  dataset_id: string
  date_from: string | null
  date_to: string | null
  queue: string | null
  summary: {
    cases_received: number
    cases_resolved: number
    backlog_end: number
    sla_breaches: number
    sla_breach_rate_pct: number | null
    throughput_to_intake_pct: number | null
    weighted_avg_resolution_hours: number | null
    reopened_cases: number
    average_daily_csat: number | null
  }
  series: MetricPoint[]
}

type Anomaly = {
  date: string
  queue: string
  metric_name: string
  actual_value: number
  baseline_median: number
  threshold_value: number
  baseline_days: number
  method: string
  severity: string
  explanation: string
}

type ManagementReport = {
  id: string
  period_from: string
  period_to: string
  narrative: string
  generation_method: string
  created_at: string
  facts: Record<string, number | string | null>
  persisted: boolean
}

type ImportIssue = { row: number | null; column: string | null; code: string; message: string }
type Preview = {
  success: boolean
  filename: string
  total_rows: number
  valid_rows: number
  date_from: string | null
  date_to: string | null
  preview_rows: Record<string, string | number | null>[]
  errors: ImportIssue[]
}
type UploadAnalysis = {
  success: boolean; filename: string; total_rows: number; valid_rows: number
  date_from: string | null; date_to: string | null; summary?: Metrics['summary']
  signal_count?: number; recommendations?: { key: string; evidence: number }[]
  errors?: ImportIssue[]
}

type PageId = 'overview' | 'queues' | 'signals' | 'recommendations' | 'reports' | 'datasets' | 'guide'
const pageIds: PageId[] = ['overview', 'queues', 'signals', 'recommendations', 'reports', 'datasets', 'guide']
function pageFromHash(): PageId {
  const page = window.location.hash.slice(1) as PageId
  return pageIds.includes(page) ? page : 'overview'
}

const queueLabels: Record<Language, Record<string, string>> = {
  en: { kyc_review: 'Customer verification · KYC', card_disputes: 'Card disputes', payments_support: 'Payment support' },
  ru: { kyc_review: 'Проверка клиентов · KYC', card_disputes: 'Споры по картам', payments_support: 'Поддержка платежей' },
}

const signalWord = (count: number, language: Language) => {
  if (language === 'en') return count === 1 ? 'signal' : 'signals'
  const lastTwo = count % 100
  const last = count % 10
  if (lastTwo >= 11 && lastTwo <= 14) return 'сигналов'
  if (last === 1) return 'сигнал'
  if (last >= 2 && last <= 4) return 'сигнала'
  return 'сигналов'
}
const numberFormat = (language: Language) => new Intl.NumberFormat(language === 'en' ? 'en-GB' : 'ru-RU')
const percent = (value: number | null, language: Language) => value === null ? translate(language, 'noData') : `${numberFormat(language).format(value)}%`
const decimal = (value: number | null, language: Language, digits = 1) => value === null ? translate(language, 'noData') : new Intl.NumberFormat(language === 'en' ? 'en-GB' : 'ru-RU', { maximumFractionDigits: digits }).format(value)
const shortDate = (value: string, language: Language) => new Date(`${value}T00:00:00`).toLocaleDateString(language === 'en' ? 'en-GB' : 'ru-RU', { day: 'numeric', month: 'short' })
const datasetLabel = (item: Dataset, language: Language) => item.source_filename === 'northstar_daily_operations.csv'
  ? (language === 'en' ? 'Northstar — 90-day operations' : 'Northstar — операции за 90 дней')
  : item.name

function issueMessage(issue: ImportIssue, language: Language) {
  if (language === 'en') return issue.message
  const known: Record<string, string> = {
    invalid_file_type: 'Загрузите файл в формате .csv.', empty_file: 'Файл пуст.', file_too_large: 'Размер файла не должен превышать 10 МБ.', unreadable_csv: 'Не удалось прочитать CSV в кодировке UTF-8.',
    no_rows: 'В CSV есть заголовок, но нет строк данных.', too_many_rows: 'В файле слишком много строк.', invalid_date: 'Укажите существующую дату в формате YYYY-MM-DD.', invalid_queue: 'Выберите kyc_review, card_disputes или payments_support.',
    invalid_number: 'В колонке должно быть указано число.', not_integer: 'Укажите целое число.', negative_value: 'Значение не может быть отрицательным.', csat_out_of_range: 'Оценка CSAT должна быть от 1 до 5 или оставлена пустой.',
    duplicate_date_queue: 'Эта дата и очередь уже указаны в другой строке.', missing_column: `Не найдена обязательная колонка «${issue.column}».`, sla_exceeds_resolved: 'Число нарушений SLA не может превышать число завершённых кейсов.', errors_truncated: 'Показаны первые 100 ошибок.',
  }
  return known[issue.code] ?? issue.message
}

function appError(message: string, language: Language) {
  if (language === 'en') return message
  const known: Record<string, string> = {
    'Dataset not found.': 'Набор данных не найден.',
    'Database is unavailable': 'База данных недоступна.',
    'CSV validation failed; no rows were imported.': 'CSV не прошёл проверку; данные не были импортированы.',
    'The request failed. Check that the API and database are running.': translate(language, 'apiUnavailable'),
  }
  return known[message] ?? message
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : detail?.message ?? `Request failed (${response.status})`
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

function weeklyTotals(points: MetricPoint[]) {
  const grouped = new Map<string, { date: string; cases_received: number; cases_resolved: number; latestBacklog: Map<string, number> }>()
  for (const point of points) {
    const date = new Date(`${point.date}T00:00:00Z`)
    date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7))
    const weekStart = date.toISOString().slice(0, 10)
    const current = grouped.get(weekStart) ?? { date: weekStart, cases_received: 0, cases_resolved: 0, latestBacklog: new Map<string, number>() }
    current.cases_received += point.cases_received
    current.cases_resolved += point.cases_resolved
    current.latestBacklog.set(point.queue, point.backlog_end)
    grouped.set(weekStart, current)
  }
  return [...grouped.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map(({ latestBacklog, ...week }) => ({ ...week, backlog_end: [...latestBacklog.values()].reduce((sum, value) => sum + value, 0) }))
}

function App() {
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem('opspilot-language') === 'ru' ? 'ru' : 'en')
  const [activePage, setActivePage] = useState<PageId>(pageFromHash)
  const t = (key: string) => translate(language, key)
  const number = numberFormat(language)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [datasetId, setDatasetId] = useState('')
  const [queue, setQueue] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [applied, setApplied] = useState({ from: '', to: '', queue: 'all' })
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [anomalyLoading, setAnomalyLoading] = useState(false)
  const [report, setReport] = useState<ManagementReport | null>(null)
  const [reportBusy, setReportBusy] = useState(false)
  const [reportError, setReportError] = useState('')
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [uploadError, setUploadError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploadAnalysis, setUploadAnalysis] = useState<UploadAnalysis | null>(null)

  useEffect(() => {
    localStorage.setItem('opspilot-language', language)
    document.documentElement.lang = language
  }, [language])

  useEffect(() => {
    const syncPage = () => setActivePage(pageFromHash())
    window.addEventListener('hashchange', syncPage)
    return () => window.removeEventListener('hashchange', syncPage)
  }, [])

  useEffect(() => {
    request<Dataset[]>('/api/v1/datasets')
      .then((items) => {
        setDatasets(items)
        if (items.length) setDatasetId(items[0].id)
        else setLoading(false)
      })
      .catch((error: Error) => { setPageError(error.message); setLoading(false) })
  }, [])

  useEffect(() => {
    const selected = datasets.find((item) => item.id === datasetId)
    if (!selected) return
    const from = selected.date_from ?? ''
    const to = selected.date_to ?? ''
    setDateFrom(from)
    setDateTo(to)
    setApplied((current) => ({ ...current, from, to }))
  }, [datasetId, datasets])

  useEffect(() => {
    if (!datasetId) return
    let cancelled = false
    const params = new URLSearchParams()
    if (applied.from) params.set('from', applied.from)
    if (applied.to) params.set('to', applied.to)
    if (applied.queue !== 'all') params.set('queue', applied.queue)
    setLoading(true)
    setPageError('')
    request<Metrics>(`/api/v1/datasets/${datasetId}/metrics?${params.toString()}`)
      .then((result) => { if (!cancelled) setMetrics(result) })
      .catch((error: Error) => { if (!cancelled) setPageError(error.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [datasetId, applied])

  useEffect(() => {
    if (!datasetId) return
    let cancelled = false
    setReport(null)
    request<ManagementReport[]>(`/api/v1/datasets/${datasetId}/reports?language=${language}`)
      .then((items) => { if (!cancelled) setReport(items[0] ?? null) })
      .catch((error: Error) => { if (!cancelled) setReportError(error.message) })
    return () => { cancelled = true }
  }, [datasetId, language])

  useEffect(() => {
    if (!datasetId) return
    let cancelled = false
    const params = new URLSearchParams()
    if (applied.from) params.set('from', applied.from)
    if (applied.to) params.set('to', applied.to)
    if (applied.queue !== 'all') params.set('queue', applied.queue)
    setAnomalyLoading(true)
    request<Anomaly[]>(`/api/v1/datasets/${datasetId}/anomalies?${params.toString()}`)
      .then((items) => { if (!cancelled) setAnomalies(items) })
      .catch((error: Error) => { if (!cancelled) setPageError(error.message) })
      .finally(() => { if (!cancelled) setAnomalyLoading(false) })
    return () => { cancelled = true }
  }, [datasetId, applied])

  const weekly = useMemo(() => weeklyTotals(metrics?.series ?? []), [metrics])
  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setApplied({ from: dateFrom, to: dateTo, queue })
  }

  async function previewFile() {
    if (!file) return
    setBusy(true)
    setUploadError('')
    setPreview(null)
    const form = new FormData()
    form.append('file', file)
    try {
      setPreview(await request<Preview>('/api/v1/datasets/preview', { method: 'POST', body: form }))
    } catch (error) {
      setUploadError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function importFile() {
    if (!file || !preview?.success) return
    setBusy(true)
    setUploadError('')
    const form = new FormData()
    form.append('file', file)
    form.append('name', file.name.replace(/\.csv$/i, ''))
    try {
      const imported = await request<{ id: string }>('/api/v1/datasets', { method: 'POST', body: form })
      const updated = await request<Dataset[]>('/api/v1/datasets')
      setDatasets(updated)
      setDatasetId(imported.id)
      setQueue('all')
      setApplied((current) => ({ ...current, queue: 'all' }))
      setPreview(null)
      setFile(null)
    } catch (error) {
      setUploadError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function analyzeUploadedFile() {
    if (!file) return
    setBusy(true)
    setUploadError('')
    setUploadAnalysis(null)
    const form = new FormData()
    form.append('file', file)
    try {
      setUploadAnalysis(await request<UploadAnalysis>('/api/v1/datasets/analyze-upload', { method: 'POST', body: form }))
    } catch (error) {
      setUploadError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function generateReport() {
    if (!datasetId || !applied.from || !applied.to) return
    setReportBusy(true)
    setReportError('')
    try {
      const result = await request<ManagementReport>(`/api/v1/datasets/${datasetId}/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_from: applied.from, period_to: applied.to, queue: applied.queue === 'all' ? null : applied.queue, language }),
      })
      setReport(result)
    } catch (error) {
      setReportError((error as Error).message)
    } finally {
      setReportBusy(false)
    }
  }

  const summary = metrics?.summary
  const flowGap = summary ? summary.cases_received - summary.cases_resolved : 0
  const queueSummary = useMemo(() => {
    const grouped = new Map<string, { queue: string; received: number; resolved: number; breaches: number; backlog: number; lastDate: string }>()
    for (const point of metrics?.series ?? []) {
      const current = grouped.get(point.queue) ?? { queue: point.queue, received: 0, resolved: 0, breaches: 0, backlog: 0, lastDate: '' }
      current.received += point.cases_received
      current.resolved += point.cases_resolved
      current.breaches += point.sla_breaches
      if (point.date >= current.lastDate) { current.lastDate = point.date; current.backlog = point.backlog_end }
      grouped.set(point.queue, current)
    }
    return [...grouped.values()].sort((a, b) => b.received - a.received)
  }, [metrics])

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#overview"><span className="brand-mark">O</span><span>OpsPilot</span></a>
        <div className="topbar-right"><span className="workspace-dot" /> {t('workspace')}</div>
        <div className="language-switch" role="group" aria-label={t('languageLabel')}>
          <button type="button" aria-pressed={language === 'en'} className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>EN</button>
          <button type="button" aria-pressed={language === 'ru'} className={language === 'ru' ? 'active' : ''} onClick={() => setLanguage('ru')}>RU</button>
        </div>
      </header>

      <div className="workspace-layout">
        <aside className="sidebar">
          <div className="sidebar-label">{t('workspaceNav')}</div>
          <nav className="side-nav" aria-label={t('workspaceNav')}>
            {pageIds.map((page, index) => <a key={page} href={`#${page}`} className={activePage === page ? 'active' : ''} aria-current={activePage === page ? 'page' : undefined}>
              <span className="nav-icon" aria-hidden="true">{['◫', '⌁', '▤', '✦', '▦', '▧', '?'][index]}</span>{t(`page_${page}`)}
            </a>)}
          </nav>
          <div className="sidebar-note"><span className="workspace-dot" />{t('synthetic')}</div>
        </aside>

      <main className="content" id={activePage}>
        <div className="page-heading">
          <div>
            <div className="eyebrow">{t('eyebrow')} <span>·</span> {t(`page_${activePage}`)}</div>
            <h1>{t(`page_${activePage}`)}</h1>
            <p className="subtitle">{t(`pageDescription_${activePage}`)}</p>
          </div>
          <div className="demo-badge"><span /> {t('synthetic')}</div>
        </div>

        {pageError && <div className="alert error-alert">{appError(pageError, language)}</div>}
        {loading && <div className="loading-card"><span className="spinner" /> {t('loadingMetrics')}</div>}
        {!loading && !datasets.length && <div className="empty-state"><h2>{t('noDatasets')}</h2><p>{t('importToStart')}</p></div>}

        {(activePage === 'overview' || activePage === 'queues') && <>
        {activePage === 'overview' && <>
        <section className="start-here" aria-label={t('guideTitle')}>
          <div className="start-here-title"><span className="start-here-mark">1</span><div><strong>{t('guideTitle')}</strong><p>{t('guideDescription')}</p></div></div>
          <div className="guide-steps">
            <div><b>{t('chooseSlice')}</b><span>{t('chooseSliceText')}</span></div>
            <div><b>{t('compareFlows')}</b><span>{t('compareFlowsText')}</span></div>
            <div><b>{t('checkBacklog')}</b><span>{t('checkBacklogText')}</span></div>
          </div>
        </section>
        </>}

        {summary && !loading && <>
          <form className="filter-bar" onSubmit={applyFilters}>
            <div className="filter-intro"><strong>{t('chooseData')}</strong><span>{t('changeFilters')}</span></div>
            <label className="filter-field dataset-field"><span>{t('dataset')}</span>
              <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>
                {datasets.map((item) => <option value={item.id} key={item.id}>{datasetLabel(item, language)}</option>)}
              </select>
            </label>
            <label className="filter-field"><span>{t('queue')}</span>
              <select value={queue} onChange={(event) => setQueue(event.target.value)}>
                <option value="all">{t('allQueues')}</option>
                {Object.keys(queueLabels.en).map((value) => <option value={value} key={value}>{queueLabels[language][value]}</option>)}
              </select>
            </label>
            <label className="filter-field date-field"><span>{t('from')}</span><input type="date" value={dateFrom} max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} /></label>
            <label className="filter-field date-field"><span>{t('to')}</span><input type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} /></label>
            <button className="primary-button filter-button" type="submit">{t('show')}</button>
          </form>

          {activePage === 'overview' && <>
          <div className="dataset-caption">
            <span>{number.format(metrics.series.length)} {t('dailyRecords')}</span>
            <span>·</span>
            <span>{metrics.date_from ? shortDate(metrics.date_from, language) : '—'} — {metrics.date_to ? shortDate(metrics.date_to, language) : '—'}</span>
            {metrics.queue && <><span>·</span><span>{queueLabels[language][metrics.queue]}</span></>}
          </div>

          <section className="kpi-grid" aria-label={t('kpiSection')}>
            <KpiCard title={t('waiting')} value={number.format(summary.backlog_end)} note={t('periodEnd')} tone="teal" />
            <KpiCard title={t('sla')} value={percent(summary.sla_breach_rate_pct, language)} note={t('slaNote').replace('{breaches}', number.format(summary.sla_breaches)).replace('{resolved}', number.format(summary.cases_resolved))} tone="amber" />
            <KpiCard title={t('incoming')} value={number.format(summary.cases_received)} note={t('newCases')} />
            <KpiCard title={t('resolved')} value={number.format(summary.cases_resolved)} note={t('processedCases')} />
            <KpiCard title={t('processingPace')} value={percent(summary.throughput_to_intake_pct, language)} note={t('flowComparison')} />
            <KpiCard title={t('resolutionTime')} value={summary.weighted_avg_resolution_hours === null ? t('noData') : `${decimal(summary.weighted_avg_resolution_hours, language)} ${language === 'en' ? 'h' : 'ч'}`} note={t('weightedResolved')} />
          </section>

          <section className="interpretation" aria-live="polite">
            <div className="interpretation-icon">i</div>
            <div>
              <strong>{flowGap > 0 ? t('moreReceived').replace('{n}', number.format(flowGap)) : flowGap < 0 ? t('moreResolved').replace('{n}', number.format(Math.abs(flowGap))) : t('sameFlow')}</strong>
              <p>{summary.average_daily_csat === null ? t('csatUnavailable') : t('csatValue').replace('{n}', decimal(summary.average_daily_csat, language, 2))} {t('flowDisclaimer')}</p>
            </div>
          </section>

          <section className="chart-grid">
            <Suspense fallback={<div className="loading-card">Загружаю графики…</div>}>
              <TrendCharts data={weekly} language={language} />
            </Suspense>
          </section>
          </>}

        </>}

        </>}

        {activePage === 'queues' && <section className="dataset-list page-panel">
          <div className="section-heading"><div><h2>{t('queuePerformance')}</h2><p>{t('queuePerformanceDescription')}</p></div><span className="signal-count">{queueSummary.length} {t('queuesCount')}</span></div>
          <div className="dataset-table-wrap"><table><thead><tr><th>{t('queue')}</th><th>{t('incoming')}</th><th>{t('resolved')}</th><th>{t('waiting')}</th><th>{t('sla')}</th></tr></thead><tbody>{queueSummary.map((item) => <tr key={item.queue}><td><strong>{queueLabels[language][item.queue] ?? item.queue}</strong></td><td>{number.format(item.received)}</td><td>{number.format(item.resolved)}</td><td>{number.format(item.backlog)}</td><td>{item.resolved ? `${decimal(item.breaches / item.resolved * 100, language, 2)}%` : t('noData')}</td></tr>)}</tbody></table></div>
        </section>}

        {activePage === 'signals' && <section className="signals-section page-panel">
          <div className="section-heading"><div><h2>{t('signals')}</h2><p>{t('ruleDescription')}</p></div><span className="signal-count">{anomalyLoading ? t('checking') : `${anomalies.length} ${signalWord(anomalies.length, language)}`}</span></div>
          {!anomalyLoading && anomalies.length === 0 && <div className="no-signals">{t('noSignals')}</div>}
          {anomalies.length > 0 && <div className="signal-list">{anomalies.map((anomaly) => <article className="signal-card" key={`${anomaly.date}-${anomaly.queue}`}>
            <div className={`signal-severity ${anomaly.severity === 'high' ? 'high' : ''}`}>{anomaly.severity === 'high' ? t('strongSpike') : t('spike')}</div>
            <div className="signal-main"><strong>{shortDate(anomaly.date, language)} · {queueLabels[language][anomaly.queue] ?? anomaly.queue}</strong><span>{number.format(anomaly.actual_value)} {t('intake')} · {t('normalThreshold')} {number.format(anomaly.threshold_value)}</span><p>{language === 'ru' ? anomaly.explanation : `Intake was ${number.format(anomaly.actual_value)} cases — above the threshold of ${number.format(anomaly.threshold_value)} (1.5 × the median of ${number.format(anomaly.baseline_median)} across ${anomaly.baseline_days} observations in the previous 28 calendar days). This flags unusual volume; it does not establish the cause.`}</p></div>
          </article>)}</div>}
        </section>}

        {activePage === 'recommendations' && <section className="recommendation-list page-panel">
          <div className="section-heading"><div><h2>{t('recommendationTitle')}</h2><p>{t('recommendationIntro')}</p></div></div>
          {!summary ? <div className="no-signals">{t('loadingMetrics')}</div> : <div className="signal-list">
            {summary.cases_received > summary.cases_resolved && <article className="signal-card"><span className="signal-severity high">{t('attentionLabel')}</span><div className="signal-main"><strong>{t('recBacklogTitle')}</strong><span>{t('recBacklogEvidence').replace('{n}', number.format(summary.cases_received - summary.cases_resolved))}</span><p>{t('recBacklogAction')}</p></div></article>}
            {summary.sla_breaches > 0 && <article className="signal-card"><span className="signal-severity">{t('reviewLabel')}</span><div className="signal-main"><strong>{t('recSlaTitle')}</strong><span>{t('recSlaEvidence').replace('{n}', number.format(summary.sla_breaches)).replace('{pct}', percent(summary.sla_breach_rate_pct, language))}</span><p>{t('recSlaAction')}</p></div></article>}
            {summary.reopened_cases > 0 && <article className="signal-card"><span className="signal-severity">{t('reviewLabel')}</span><div className="signal-main"><strong>{t('recReopenedTitle')}</strong><span>{t('recReopenedEvidence').replace('{n}', number.format(summary.reopened_cases))}</span><p>{t('recReopenedAction')}</p></div></article>}
            {summary.cases_received <= summary.cases_resolved && summary.sla_breaches === 0 && summary.reopened_cases === 0 && <div className="no-signals">{t('noRecommendations')}</div>}
            <p className="data-boundary">{t('recommendationCaveat')}</p>
          </div>}
        </section>}

        {activePage === 'reports' && <section className="report-section page-panel">
          <div className="section-heading"><div><h2>{t('reportTitle')}</h2><p>{t('reportDescription')}</p></div><button className="primary-button" type="button" disabled={reportBusy || !metrics?.series.length} onClick={generateReport}>{reportBusy ? t('creatingReport') : t('createReport')}</button></div>
          {reportError && <div className="alert error-alert">{appError(reportError, language)}</div>}
          {report && <article className="report-card"><div className="report-meta">{t('templateReport')} · {shortDate(report.period_from, language)} — {shortDate(report.period_to, language)} · {report.persisted ? t('savedIn') : t('temporaryReport')}</div><p>{report.narrative}</p><small>{t('reportNoAi')}</small></article>}
          {!report && <div className="no-signals">{t('reportsEmpty')}</div>}
        </section>}

        {activePage === 'datasets' && <>
          <section className="dataset-list page-panel">
            <div className="section-heading"><div><h2>{t('datasetCatalog')}</h2><p>{t('datasetCatalogDescription')}</p></div><span className="signal-count">{datasets.length} {t('datasetsCount')}</span></div>
            <div className="dataset-table-wrap"><table><thead><tr><th>{t('dataset')}</th><th>{t('source')}</th><th>{t('rowsLabel')}</th><th>{t('coverage')}</th></tr></thead><tbody>{datasets.map((item) => <tr key={item.id}><td><strong>{datasetLabel(item, language)}</strong></td><td>{item.source_filename}</td><td>{number.format(item.row_count)}</td><td>{item.date_from ? shortDate(item.date_from, language) : '—'} — {item.date_to ? shortDate(item.date_to, language) : '—'}</td></tr>)}</tbody></table></div>
            {import.meta.env.VITE_PUBLIC_DEMO === 'true' && <p className="data-boundary">{t('publicUploadNote')}</p>}
          </section>
          {import.meta.env.VITE_PUBLIC_DEMO === 'true' ? <details open className="upload-panel">
          <summary><span><strong>{t('analyzeCsv')}</strong><small>{t('analyzeCsvHint')}</small></span><span className="summary-plus">+</span></summary>
          <div className="upload-content">
            <p>{t('uploadDescription')} {t('uploadPrivacyNote')}</p>
            <a className="text-link" href="/api/v1/sample-data" download>{t('downloadTemplate')}</a>
            <div className="upload-actions"><input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setUploadAnalysis(null); setUploadError('') }} />
              <button className="secondary-button" type="button" disabled={!file || busy} onClick={analyzeUploadedFile}>{busy ? t('analyzingCsv') : t('analyzeCsv')}</button>
            </div>
            {uploadError && <div className="alert error-alert">{appError(uploadError, language)}</div>}
            {uploadAnalysis && <div className={`preview-result ${uploadAnalysis.success ? 'preview-ok' : 'preview-bad'}`}>
              <strong>{uploadAnalysis.success ? t('analysisComplete') : t('invalidFile')}</strong>
              <p>{uploadAnalysis.valid_rows} / {uploadAnalysis.total_rows} {t('rows')} · {uploadAnalysis.date_from ? shortDate(uploadAnalysis.date_from, language) : '—'} — {uploadAnalysis.date_to ? shortDate(uploadAnalysis.date_to, language) : '—'}</p>
              {uploadAnalysis.errors?.length ? <ul className="issue-list">{uploadAnalysis.errors.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.row ? `${language === 'en' ? 'Row' : 'Строка'} ${issue.row}: ` : ''}{issueMessage(issue, language)}</li>)}</ul> : uploadAnalysis.summary && <>
                <div className="upload-kpi-grid"><span>{t('incoming')} <strong>{number.format(uploadAnalysis.summary.cases_received)}</strong></span><span>{t('resolved')} <strong>{number.format(uploadAnalysis.summary.cases_resolved)}</strong></span><span>{t('waiting')} <strong>{number.format(uploadAnalysis.summary.backlog_end)}</strong></span><span>{t('sla')} <strong>{percent(uploadAnalysis.summary.sla_breach_rate_pct, language)}</strong></span></div>
                <p>{t('uploadSignals').replace('{n}', String(uploadAnalysis.signal_count ?? 0))} · {t('uploadRecommendationCount').replace('{n}', String(uploadAnalysis.recommendations?.length ?? 0))}</p>
                {!!uploadAnalysis.recommendations?.length && <div className="signal-list">{uploadAnalysis.recommendations.map((item) => {
                  const definition = item.key === 'inflow_exceeds_resolved'
                    ? { title: 'recBacklogTitle', evidence: t('recBacklogEvidence').replace('{n}', number.format(item.evidence)), action: 'recBacklogAction' }
                    : item.key === 'review_sla_breaches'
                      ? { title: 'recSlaTitle', evidence: t('recSlaEvidence').replace('{n}', number.format(item.evidence)).replace('{pct}', percent(uploadAnalysis.summary!.sla_breach_rate_pct, language)), action: 'recSlaAction' }
                      : { title: 'recReopenedTitle', evidence: t('recReopenedEvidence').replace('{n}', number.format(item.evidence)), action: 'recReopenedAction' }
                  return <article className="signal-card" key={item.key}><div className="signal-main"><strong>{t(definition.title)}</strong><span>{definition.evidence}</span><p>{t(definition.action)}</p></div></article>
                })}</div>}
                <small>{t('uploadNotSaved')}</small>
              </>}
            </div>}
          </div></details> : <details open className="upload-panel">
          <summary><span><strong>{datasets.length ? t('uploadOther') : t('upload')}</strong><small>{t('uploadHint')}</small></span><span className="summary-plus">+</span></summary>
          <div className="upload-content">
            <p>{t('uploadDescription')}</p>
            <a className="text-link" href="/api/v1/sample-data" download>{t('downloadTemplate')}</a>
            <div className="upload-actions">
              <input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); setUploadError('') }} />
              <button className="secondary-button" type="button" disabled={!file || busy} onClick={previewFile}>{busy ? t('checkingCsv') : t('checkCsv')}</button>
            </div>
            {uploadError && <div className="alert error-alert">{appError(uploadError, language)}</div>}
            {preview && <div className={`preview-result ${preview.success ? 'preview-ok' : 'preview-bad'}`}>
              <strong>{preview.success ? t('validFile') : t('invalidFile')}</strong>
              <p>{preview.valid_rows} / {preview.total_rows} {t('rows')} · {preview.date_from ? shortDate(preview.date_from, language) : '—'} — {preview.date_to ? shortDate(preview.date_to, language) : '—'}</p>
              {preview.errors.length > 0 && <ul className="issue-list">{preview.errors.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.row ? `${language === 'en' ? 'Row' : 'Строка'} ${issue.row}: ` : ''}{issueMessage(issue, language)}</li>)}</ul>}
              {preview.success && <>
                <div className="table-scroll"><table><thead><tr><th>{t('date')}</th><th>{t('queueColumn')}</th><th>{t('incomingColumn')}</th><th>{t('resolvedColumn')}</th><th>{t('waitingColumn')}</th></tr></thead><tbody>{preview.preview_rows.slice(0, 3).map((row, index) => <tr key={index}><td>{String(row.date)}</td><td>{queueLabels[language][String(row.queue)] ?? String(row.queue)}</td><td>{String(row.cases_received)}</td><td>{String(row.cases_resolved)}</td><td>{String(row.backlog_end)}</td></tr>)}</tbody></table></div>
                <button className="primary-button import-button" type="button" disabled={busy} onClick={importFile}>{busy ? t('importing') : t('importVerified')}</button>
              </>}
            </div>}
          </div>
          </details>}
        </>}

        {activePage === 'guide' && <section className="metric-guide-page page-panel">
          <div className="guide-intro"><span className="start-here-mark">?</span><div><strong>{t('guideIntroTitle')}</strong><p>{t('guideIntroDescription')}</p></div></div>
          <div className="metric-definitions">
            <article><strong>{t('waiting')}</strong><p>{t('backlogDefinition')}</p></article>
            <article><strong>SLA</strong><p>{t('slaDefinition')}</p></article>
            <article><strong>{t('processingPace')}</strong><p>{t('paceDefinition')}</p></article>
            <article><strong>{t('resolutionTime')}</strong><p>{t('timeDefinition')}</p></article>
            <article><strong>CSAT</strong><p>{t('csatGuide')}</p></article>
          </div>
          <div className="guide-caveat"><strong>{t('guideCaveatTitle')}</strong><p>{t('guideCaveatText')}</p></div>
        </section>}

        <footer className="page-footer">OpsPilot <span>·</span> {t('footer')}</footer>
      </main>
      </div>
    </div>
  )
}

function KpiCard({ title, value, note, tone = 'default' }: { title: string; value: string; note: string; tone?: 'default' | 'teal' | 'amber' }) {
  return <article className={`kpi-card ${tone}`}><div className="kpi-title">{title}</div><div className="kpi-value">{value}</div><div className="kpi-note">{note}</div></article>
}

export default App
