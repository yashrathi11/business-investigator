import { useEffect, useRef, useState } from "react"
import type { ElementType, ReactNode, FormEvent, ChangeEvent } from "react"

import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Bell,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Database,
  FileText,
  LayoutDashboard,
  Search,
  Settings,
  ShieldAlert,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Target,
  TrendingUp,
  Upload,
  WalletCards,
  Users,
} from "lucide-react"

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import "./App.css"

type Page =
  | "overview"
  | "analytics"
  | "anomalies"
  | "investigations"
  | "forecast"
  | "settings"
  | "system"
  | "about"

type DatasetSummary = {
  total_revenue: number
  total_orders: number
  total_customers: number
  total_units_sold: number
  average_order_value: number
  average_revenue_per_customer: number
}

type DatasetMetadata = {
  dataset_id: string
  filename: string
  input_rows?: number | null
  output_rows?: number | null
  total_revenue?: number | null
  created_at?: string | null
  source?: string | null
}

type AnalyticsData = {
  kpis: {
    average_order_value: number
    revenue_per_customer: number
    repeat_customer_rate: number
    units_sold: number
  }
  daily_revenue: Array<{
    date: string
    actual: number
    expected: number
  }>
  monthly_revenue: Array<{
    month: string
    revenue: number
  }>
  top_products: Array<{
    product: string
    revenue: number
    share: number
  }>
}

type Anomaly = {
  InvoiceDate: string
  date: string
  revenue: number
  actual: number
  expected: number
  rolling_mean_30: number
  z_score: number
  severity: string
  revenue_impact: number
}

type InvestigationData = {
  status: string
  anomaly_date: string
  report: unknown
  summary: unknown
  evidence: unknown
  explanation: string
}

const API_BASE_URL = "http://127.0.0.1:8000"


const navItems: {
  id: Page
  label: string
  icon: ElementType
  count?: number
}[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "anomalies", label: "Anomalies", icon: AlertTriangle, count: 1 },
  { id: "investigations", label: "Investigations", icon: Target },
  { id: "forecast", label: "Forecast", icon: TrendingUp },
]

const secondaryItems: {
  id: Page
  label: string
  icon: ElementType
}[] = [
  { id: "settings", label: "Settings", icon: Settings },
  { id: "system", label: "System", icon: ShieldCheck },
]

function formatCurrency(value: number) {
  return `£${value.toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function App() {
  const [activePage, setActivePage] = useState<Page>("overview")
  const [datasetId, setDatasetId] = useState("")
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([])
  const [datasetsLoading, setDatasetsLoading] = useState(true)
  const [summary, setSummary] = useState<DatasetSummary | null>(null)
  const [criticalAnomaly, setCriticalAnomaly] = useState<Anomaly | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [anomalyFilter, setAnomalyFilter] = useState("ALL")
  const [anomalySort, setAnomalySort] = useState("severity")
  const [apiLoading, setApiLoading] = useState(true)
  const [apiError, setApiError] = useState("")
  const [uploading, setUploading] = useState(false)
  const [investigation, setInvestigation] =
    useState<InvestigationData | null>(null)
  const [investigationLoading, setInvestigationLoading] = useState(false)
  const [investigationError, setInvestigationError] = useState("")
  const [reportLoading, setReportLoading] = useState(false)

  // UI preferences / interactions
  const [searchQuery, setSearchQuery] = useState("")
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [workspaceName, setWorkspaceName] = useState("Business Investigator")
  const [investigationMode, setInvestigationMode] = useState(true)
  const [criticalAlerts, setCriticalAlerts] = useState(true)
  const [forecastUpdates, setForecastUpdates] = useState(false)
  const [settingsMessage, setSettingsMessage] = useState("")

  useEffect(() => {
    let cancelled = false

    async function loadDatasets() {
      try {
        setDatasetsLoading(true)
        const response = await fetch(`${API_BASE_URL}/datasets`)
        const result = await response.json()

        if (!response.ok) {
          throw new Error(result.detail ?? "Failed to load datasets.")
        }

        const loaded: DatasetMetadata[] = Array.isArray(result.datasets)
          ? result.datasets
              .map((item: any) => ({
                dataset_id: String(item.dataset_id ?? ""),
                filename: String(item.filename ?? "Processed dataset"),
                input_rows: item.input_rows == null ? null : Number(item.input_rows),
                output_rows: item.output_rows == null ? null : Number(item.output_rows),
                total_revenue: item.total_revenue == null ? null : Number(item.total_revenue),
                created_at: item.created_at ?? null,
                source: item.source ?? null,
              }))
              .filter((item: DatasetMetadata) => item.dataset_id)
          : []

        if (cancelled) return

        setDatasets(loaded)

        if (loaded.length) {
          setDatasetId((current) =>
            loaded.some((item: DatasetMetadata) => item.dataset_id === current)
              ? current
              : loaded[0].dataset_id,
          )
        } else {
          setDatasetId("")
          setApiError("No processed datasets are available. Upload a dataset to begin.")
        }
      } catch (error) {
        if (!cancelled) {
          setApiError(
            error instanceof Error
              ? error.message
              : "Unable to load available datasets.",
          )
        }
      } finally {
        if (!cancelled) {
          setDatasetsLoading(false)
        }
      }
    }

    loadDatasets()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setInvestigation(null)
    setInvestigationError("")

    let cancelled = false

    async function loadData() {
      if (!datasetId) {
        setSummary(null)
        setAnalyticsData(null)
        setAnomalies([])
        setCriticalAnomaly(null)
        setApiLoading(datasetsLoading)
        return
      }

      try {
        setApiLoading(true)
        setApiError("")

        const [summaryResponse, anomalyResponse, analyticsResponse] =
          await Promise.all([
            fetch(`${API_BASE_URL}/summary/${datasetId}`),
            fetch(`${API_BASE_URL}/anomalies/${datasetId}`),
            fetch(`${API_BASE_URL}/analytics/${datasetId}`),
          ])

        if (!summaryResponse.ok) {
          throw new Error("Failed to load dataset summary.")
        }

        if (!anomalyResponse.ok) {
          throw new Error("Failed to load anomaly data.")
        }

        if (!analyticsResponse.ok) {
          throw new Error("Failed to load analytics data.")
        }

        const summaryData = await summaryResponse.json()
        const anomalyData = await anomalyResponse.json()
        const analyticsResult = await analyticsResponse.json()

        if (cancelled) return

        setSummary(summaryData.summary)
        setAnalyticsData(analyticsResult)

        const loadedAnomalies: Anomaly[] = Array.isArray(anomalyData.anomalies)
          ? anomalyData.anomalies.map((item: any) => ({
              ...item,
              InvoiceDate: String(item.InvoiceDate ?? item.date ?? ""),
              date: String(item.date ?? item.InvoiceDate ?? ""),
              revenue: Number(item.revenue ?? item.actual ?? 0),
              actual: Number(item.actual ?? item.revenue ?? 0),
              expected: Number(item.expected ?? item.rolling_mean_30 ?? 0),
              rolling_mean_30: Number(item.rolling_mean_30 ?? item.expected ?? 0),
              z_score: Number(item.z_score ?? 0),
              severity: String(item.severity ?? "LOW"),
              revenue_impact: Number(item.revenue_impact ?? 0),
            }))
          : []

        setAnomalies(loadedAnomalies)

        const critical =
          loadedAnomalies
            .filter((item) => item.severity === "CRITICAL")
            .sort(
              (a, b) => Math.abs(b.z_score) - Math.abs(a.z_score),
            )[0] ?? null

        setCriticalAnomaly(critical)
      } catch (error) {
        if (!cancelled) {
          setApiError(
            error instanceof Error
              ? error.message
              : "Unable to connect to the API.",
          )
        }
      } finally {
        if (!cancelled) {
          setApiLoading(false)
        }
      }
    }

    loadData()

    return () => {
      cancelled = true
    }
  }, [datasetId, datasetsLoading])

  async function handleUpload(file: File) {
    try {
      setUploading(true)
      setApiError("")

      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? "Dataset upload failed.")
      }

      const uploadedDatasetId = String(data.dataset_id ?? "")

      if (!uploadedDatasetId) {
        throw new Error("Upload succeeded but no dataset ID was returned.")
      }

      const uploadedMetadata: DatasetMetadata = {
        ...(data.dataset ?? {}),
        dataset_id: uploadedDatasetId,
        filename: String(data.dataset?.filename ?? file.name),
      }

      setDatasets((current) => [
        uploadedMetadata,
        ...current.filter((item) => item.dataset_id !== uploadedDatasetId),
      ])
      setDatasetId(uploadedDatasetId)
      setActivePage("overview")
    } catch (error) {
      setApiError(
        error instanceof Error
          ? error.message
          : "Dataset upload failed.",
      )
    } finally {
      setUploading(false)
    }
  }


  async function openInvestigationFor(anomaly: Anomaly) {
    if (!anomaly.InvoiceDate || anomaly.severity === "NORMAL") {
      setInvestigationError("This event is not eligible for investigation.")
      setActivePage("investigations")
      return
    }

    try {
      setActivePage("investigations")
      setInvestigationLoading(true)
      setInvestigationError("")

      const anomalyDate = anomaly.InvoiceDate.slice(0, 10)

      const response = await fetch(
        `${API_BASE_URL}/investigate/${datasetId}/${anomalyDate}`,
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? "Investigation failed.")
      }

      setInvestigation(data as InvestigationData)
    } catch (error) {
      setInvestigationError(
        error instanceof Error
          ? error.message
          : "Investigation failed.",
      )
    } finally {
      setInvestigationLoading(false)
    }
  }

  async function openInvestigation() {
    if (!criticalAnomaly?.InvoiceDate) {
      setInvestigationError("There is no critical anomaly to investigate.")
      setActivePage("investigations")
      return
    }

    const anomalyDate = criticalAnomaly.InvoiceDate.slice(0, 10)

    try {
      setActivePage("investigations")
      setInvestigationLoading(true)
      setInvestigationError("")

      const response = await fetch(
        `${API_BASE_URL}/investigate/${datasetId}/${anomalyDate}`,
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? "Investigation failed.")
      }

      setInvestigation(data as InvestigationData)
    } catch (error) {
      setInvestigationError(
        error instanceof Error
          ? error.message
          : "Investigation failed.",
      )
    } finally {
      setInvestigationLoading(false)
    }
  }

  async function exportInvestigationReport() {
    if (!criticalAnomaly?.InvoiceDate) return

    try {
      setReportLoading(true)

      const anomalyDate = criticalAnomaly.InvoiceDate.slice(0, 10)

      const response = await fetch(
        `${API_BASE_URL}/report/${datasetId}/${anomalyDate}`,
      )

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail ?? "Report export failed.")
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")

      link.href = url
      link.download = `business-investigator-${anomalyDate}.pdf`

      document.body.appendChild(link)
      link.click()
      link.remove()

      window.URL.revokeObjectURL(url)
    } catch (error) {
      setInvestigationError(
        error instanceof Error
          ? error.message
          : "Report export failed.",
      )
    } finally {
      setReportLoading(false)
    }
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const query = searchQuery.trim().toLowerCase()
    if (!query) return

    const routes: Array<[string[], Page]> = [
      [["overview", "dashboard", "home"], "overview"],
      [["analytics", "revenue", "customer", "sales"], "analytics"],
      [["anomaly", "anomalies", "alert", "alerts"], "anomalies"],
      [["investigation", "investigations", "root cause"], "investigations"],
      [["forecast", "prediction", "xgboost"], "forecast"],
      [["settings", "preference", "preferences"], "settings"],
      [["system", "health", "status"], "system"],
      [["about", "business investigator"], "about"],
    ]

    const match = routes.find(([keywords]) =>
      keywords.some((keyword) => query.includes(keyword)),
    )

    if (match) {
      setActivePage(match[1])
      setNotificationsOpen(false)
      return
    }

    if (
      criticalAnomaly?.InvoiceDate &&
      criticalAnomaly.InvoiceDate.slice(0, 10).includes(query)
    ) {
      openInvestigation()
      return
    }

    setApiError(`No dashboard result found for "${searchQuery}".`)
  }

  function editWorkspaceName() {
    const nextName = window.prompt(
      "Enter workspace name:",
      workspaceName,
    )?.trim()

    if (nextName) {
      setWorkspaceName(nextName)
      setSettingsMessage("Workspace name updated.")
    }
  }

  function changeDefaultDataset() {
    setActivePage("overview")
    setSettingsMessage(
      datasets.length
        ? "Use the dataset selector in the top bar to switch datasets."
        : "Upload a dataset from the Overview page to get started.",
    )
  }

  function toggleInvestigationMode() {
    setInvestigationMode((value: boolean) => !value)
    setSettingsMessage(
      investigationMode
        ? "Investigation mode turned off."
        : "Evidence-backed investigation mode turned on.",
    )
  }

  function toggleCriticalAlerts() {
    setCriticalAlerts((value: boolean) => !value)
    setSettingsMessage(
      criticalAlerts
        ? "Critical anomaly notifications turned off."
        : "Critical anomaly notifications turned on.",
    )
  }

  function toggleForecastUpdates() {
    setForecastUpdates((value: boolean) => !value)
    setSettingsMessage(
      forecastUpdates
        ? "Forecast update notifications turned off."
        : "Forecast update notifications turned on.",
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">BI</div>
          <div className="brand-copy">
            <strong>Business</strong>
            <span>Investigator</span>
          </div>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={`sidebar-link ${activePage === item.id ? "active" : ""}`}
                onClick={() => setActivePage(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
                {item.id === "anomalies" && anomalies.length > 0 ? (
                  <span className="nav-count">{anomalies.length}</span>
                ) : item.count ? (
                  <span className="nav-count">{item.count}</span>
                ) : null}
              </button>
            )
          })}
        </nav>

        <div className="sidebar-divider" />

        <nav className="sidebar-nav secondary">
          {secondaryItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={`sidebar-link ${activePage === item.id ? "active" : ""}`}
                onClick={() => setActivePage(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="sidebar-spacer" />

        <div className="system-card">
          <div className="system-indicator" />
          <div>
            <strong>System Online</strong>
            <span>All services operational</span>
          </div>
        </div>

        <button
          className={`about-link ${activePage === "about" ? "about-active" : ""}`}
          onClick={() => setActivePage("about")}
        >
          <div>
            <strong>About Business Investigator</strong>
            <span>Turning data into decisions.</span>
          </div>
          <ChevronRight size={16} />
        </button>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div className="welcome">
            <span className="eyebrow">BUSINESS INTELLIGENCE</span>
            <h1>
              {activePage === "overview" && "Welcome back, here's your dashboard"}
              {activePage === "analytics" && "Analytics"}
              {activePage === "anomalies" && "Anomaly center"}
              {activePage === "investigations" && "Investigations"}
              {activePage === "forecast" && "Revenue forecast"}
              {activePage === "settings" && "Settings"}
              {activePage === "system" && "System status"}
              {activePage === "about" && "About Business Investigator"}
            </h1>
            <p>
              {activePage === "overview" &&
                "Here's what's happening with your business today."}
              {activePage === "analytics" &&
                "Explore performance, contribution and business trends."}
              {activePage === "anomalies" &&
                "Review unusual business events detected by the intelligence engine."}
              {activePage === "investigations" &&
                "Trace anomalies back to their strongest evidence and root causes."}
              {activePage === "forecast" &&
                "Understand the expected revenue trajectory for the next seven days."}
              {activePage === "settings" &&
                "Configure your workspace and investigation preferences."}
              {activePage === "system" &&
                "Monitor the health of your analytics and intelligence pipeline."}
              {activePage === "about" &&
                "A business intelligence system built to turn raw data into decisions."}
            </p>
          </div>

          <div className="header-actions">
            <form className="search-box" onSubmit={handleSearchSubmit}>
              <Search size={17} />
              <input
                type="text"
                value={searchQuery}
                onChange={(event: ChangeEvent<HTMLInputElement>) => {
                  setSearchQuery(event.target.value)
                  if (apiError) setApiError("")
                }}
                placeholder="Search pages, revenue, anomalies..."
                aria-label="Search dashboard"
              />
            </form>

            <div className="dataset-selector-wrap">
              <Database size={16} />
              <select
                className="dataset-selector"
                value={datasetId}
                onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                  setDatasetId(event.target.value)
                  setInvestigation(null)
                  setInvestigationError("")
                  setActivePage("overview")
                }}
                disabled={datasetsLoading || !datasets.length}
                aria-label="Select dataset"
              >
                {!datasets.length && (
                  <option value="">
                    {datasetsLoading ? "Loading datasets..." : "No datasets"}
                  </option>
                )}
                {datasets.map((dataset) => (
                  <option key={dataset.dataset_id} value={dataset.dataset_id}>
                    {dataset.filename}
                  </option>
                ))}
              </select>
            </div>

            <div className="notification-wrap">
              <button
                className="icon-button"
                onClick={() => setNotificationsOpen((value: boolean) => !value)}
                aria-label="Notifications"
                type="button"
              >
                <Bell size={18} />
                {criticalAnomaly && criticalAlerts && (
                  <span className="notification-dot" />
                )}
              </button>

              {notificationsOpen && (
                <div className="notification-popover">
                  <div className="notification-popover-header">
                    <strong>Notifications</strong>
                    <span>{criticalAnomaly && criticalAlerts ? "1 new" : "All clear"}</span>
                  </div>

                  {criticalAnomaly && criticalAlerts ? (
                    <button
                      className="notification-item"
                      type="button"
                      onClick={() => {
                        setNotificationsOpen(false)
                        openInvestigation()
                      }}
                    >
                      <span className="notification-item-icon">
                        <AlertTriangle size={15} />
                      </span>
                      <span>
                        <strong>Critical revenue anomaly</strong>
                        <small>
                          {criticalAnomaly.InvoiceDate?.slice(0, 10)} requires investigation.
                        </small>
                      </span>
                      <ChevronRight size={15} />
                    </button>
                  ) : (
                    <div className="notification-empty">
                      <CheckCircle2 size={17} />
                      <span>No new critical alerts.</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="profile-avatar">YR</div>

            <div className="date-box">
              <CalendarDays size={16} />
              <div>
                <strong>
                   {new Date()
                     .toLocaleDateString("en-GB", {
                        day: "2-digit",
                        month: "short",
                         year: "numeric",
                  })
                   .replace("Sept", "Sep")}
                </strong>
                <span>Today</span>
              </div>
            </div>
          </div>
        </header>

        {apiError && (
          <div className="api-status error app-api-banner">
            <AlertTriangle size={14} />
            <span>{apiError}</span>
            <button
              type="button"
              className="api-banner-dismiss"
              onClick={() => setApiError("")}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        {activePage === "overview" && (
          <Overview
            summary={summary}
            analyticsData={analyticsData}
            criticalAnomaly={criticalAnomaly}
            loading={apiLoading}
            uploading={uploading}
            onUpload={handleUpload}
            onInvestigate={openInvestigation}
          />
        )}

        {activePage === "analytics" && (
          <Analytics data={analyticsData} loading={apiLoading} />
        )}
        {activePage === "anomalies" && (
          <Anomalies
            anomalies={anomalies}
            filter={anomalyFilter}
            sort={anomalySort}
            onFilterChange={setAnomalyFilter}
            onSortChange={setAnomalySort}
            onInvestigate={(item) => openInvestigationFor(item)}
          />
        )}
        {activePage === "investigations" && (
          <Investigations
            investigation={investigation}
            loading={investigationLoading}
            error={investigationError}
            onExport={exportInvestigationReport}
            reportLoading={reportLoading}
          />
        )}
        {activePage === "forecast" && <Forecast datasetId={datasetId} />}
        {activePage === "settings" && (
          <SettingsPage
            workspaceName={workspaceName}
            datasetName={
              datasets.find((item) => item.dataset_id === datasetId)?.filename ??
              "No dataset selected"
            }
            investigationMode={investigationMode}
            criticalAlerts={criticalAlerts}
            forecastUpdates={forecastUpdates}
            message={settingsMessage}
            onEditWorkspace={editWorkspaceName}
            onChangeDataset={changeDefaultDataset}
            onToggleInvestigationMode={toggleInvestigationMode}
            onToggleCriticalAlerts={toggleCriticalAlerts}
            onToggleForecastUpdates={toggleForecastUpdates}
          />
        )}
        {activePage === "system" && <SystemPage />}
        {activePage === "about" && <AboutPage />}
      </main>
    </div>
  )
}

function Overview({
  summary,
  analyticsData,
  criticalAnomaly,
  onInvestigate,
  loading,
  uploading,
  onUpload,
}: {
  summary: DatasetSummary | null
  analyticsData: AnalyticsData | null
  criticalAnomaly: Anomaly | null
  onInvestigate: () => void
  loading: boolean
  uploading: boolean
  onUpload: (file: File) => void
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const daily = Array.isArray(analyticsData?.daily_revenue) ? analyticsData.daily_revenue : []

  const chartData = daily.slice(-90).map((item: any) => ({
    date: String(item.date ?? item.InvoiceDate ?? ""),
    revenue: Number(item.actual ?? item.revenue ?? 0),
    orders: 0,
    customers: 0,
    units: 0,
  }))

  const revenueTotal = Number(summary?.total_revenue ?? 0)
  const ordersTotal = Number(summary?.total_orders ?? 0)
  const customersTotal = Number(summary?.total_customers ?? 0)
  const unitsTotal = Number(summary?.total_units_sold ?? 0)
  const aov = Number(summary?.average_order_value ?? 0)

  const latest = chartData[chartData.length - 1]
  const previous = chartData.length > 1 ? chartData[chartData.length - 2] : null

  const revenueDelta =
    latest && previous && previous.revenue !== 0
      ? ((latest.revenue - previous.revenue) / Math.abs(previous.revenue)) * 100
      : null

  const maxRevenue = Math.max(...chartData.map((item) => item.revenue), 1)

  return (
    <>
      <PageToolbar
        eyebrow="EXECUTIVE OVERVIEW"
        title="Business performance"
        description="A live operating view of revenue, demand and investigation signals."
        action={
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) {
                  onUpload(file)
                  event.currentTarget.value = ""
                }
              }}
            />
            <button
              type="button"
              className="secondary-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <Upload size={15} />
              {uploading ? "Uploading..." : "Upload dataset"}
            </button>
          </>
        }
      />

      <section className="kpi-grid">
        <KpiCard
          title="Total Revenue"
          value={loading ? "Loading..." : formatCurrency(revenueTotal)}
          change={latest ? "Live dataset" : "Awaiting data"}
          icon={<TrendingUp size={17} />}
        />
        <KpiCard
          title="Orders"
          value={loading ? "Loading..." : ordersTotal.toLocaleString("en-GB")}
          change="Completed orders"
          icon={<ShoppingCart size={17} />}
        />
        <KpiCard
          title="Customers"
          value={loading ? "Loading..." : customersTotal.toLocaleString("en-GB")}
          change="Unique customers"
          icon={<Users size={17} />}
        />
        <KpiCard
          title="Average Order Value"
          value={loading ? "Loading..." : formatCurrency(aov)}
          change="Revenue / order"
          icon={<WalletCards size={17} />}
        />
      </section>

      <section className="overview-main-grid">
        <div className="panel revenue-overview-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">REVENUE TREND</span>
              <h2>Daily revenue</h2>
              <p>Last 90 available business days from the selected dataset.</p>
            </div>

            <span className="live-badge">
              <i />
              LIVE
            </span>
          </div>

          <div className="large-chart overview-revenue-chart">
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="overviewRevenueFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ff3f48" stopOpacity={0.18} />
                      <stop offset="100%" stopColor="#ff3f48" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#edf0f4" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#98a2b3" }}
                    minTickGap={34}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#98a2b3" }}
                    tickFormatter={(value: number) =>
                      `£${Math.round(Number(value) / 1000)}K`
                    }
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(Number(value ?? 0)), "Revenue"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#ff3f48"
                    strokeWidth={2.2}
                    fill="url(#overviewRevenueFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="overview-empty-state">
                <Activity size={20} />
                <strong>No daily analytics available</strong>
                <span>Upload or select a dataset to populate this view.</span>
              </div>
            )}
          </div>

          <div className="overview-chart-footer">
            <span>
              <i className="legend-dot actual" />
              Revenue
            </span>
            {revenueDelta !== null && (
              <span className={revenueDelta >= 0 ? "metric-positive" : "metric-negative"}>
                {revenueDelta >= 0 ? "+" : ""}
                {revenueDelta.toFixed(1)}% vs previous day
              </span>
            )}
          </div>
        </div>

        <div className="panel signal-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">INVESTIGATION SIGNAL</span>
              <h2>Priority finding</h2>
              <p>The highest-severity anomaly currently available.</p>
            </div>
            <ShieldAlert size={18} />
          </div>

          {criticalAnomaly ? (
            <>
              <div className="priority-severity">
                <span className={`severity-pill ${criticalAnomaly.severity.toLowerCase()}`}>
                  {criticalAnomaly.severity}
                </span>
                <span>{criticalAnomaly.date}</span>
              </div>

              <div className="priority-value">
                <strong>{formatCurrency(criticalAnomaly.actual)}</strong>
                <span>actual revenue</span>
              </div>

              <div className="priority-grid">
                <div>
                  <span>Expected</span>
                  <strong>{formatCurrency(criticalAnomaly.expected)}</strong>
                </div>
                <div>
                  <span>Z-score</span>
                  <strong>{Number(criticalAnomaly.z_score).toFixed(2)}</strong>
                </div>
                <div>
                  <span>Impact</span>
                  <strong>
                    {criticalAnomaly.revenue_impact >= 0 ? "+" : ""}
                    {Number(criticalAnomaly.revenue_impact).toFixed(1)}%
                  </strong>
                </div>
                <div>
                  <span>Detection</span>
                  <strong>30D baseline</strong>
                </div>
              </div>

              <button
                type="button"
                className="primary-button full-width"
                onClick={onInvestigate}
              >
                Review finding
                <ArrowUpRight size={15} />
              </button>
            </>
          ) : (
            <div className="overview-empty-state compact">
              <ShieldCheck size={22} />
              <strong>No critical anomaly</strong>
              <span>The investigation queue is currently clear.</span>
            </div>
          )}
        </div>
      </section>

      <section className="overview-secondary-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">OPERATING VOLUME</span>
              <h2>Daily activity</h2>
              <p>Orders and customer activity across the latest period.</p>
            </div>
          </div>

          <div className="mini-metric-grid">
            <div className="mini-metric-card">
              <span>Net units sold</span>
              <strong>{unitsTotal.toLocaleString("en-GB")}</strong>
              <small>Across the dataset</small>
            </div>
            <div className="mini-metric-card">
              <span>Latest orders</span>
              <strong>{latest ? latest.orders.toLocaleString("en-GB") : "—"}</strong>
              <small>Most recent business day</small>
            </div>
            <div className="mini-metric-card">
              <span>Latest customers</span>
              <strong>
                {latest ? latest.customers.toLocaleString("en-GB") : "—"}
              </strong>
              <small>Active customer count</small>
            </div>
          </div>

          <div className="volume-bars">
            {chartData.slice(-14).map((item) => (
              <div className="volume-bar-column" key={item.date}>
                <div className="volume-bar-track">
                  <div
                    className="volume-bar-fill"
                    style={{
                      height: `${Math.max(5, (item.revenue / maxRevenue) * 100)}%`,
                    }}
                    title={`${item.date}: ${formatCurrency(item.revenue)}`}
                  />
                </div>
                <span>{item.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">DATASET STATUS</span>
              <h2>Investigation readiness</h2>
              <p>Checks that determine whether the intelligence layer is ready.</p>
            </div>
            <CheckCircle2 size={18} />
          </div>

          <div className="readiness-list">
            <div className="readiness-row">
              <span><i /> Dataset loaded</span>
              <strong>Ready</strong>
            </div>
            <div className="readiness-row">
              <span><i /> KPI engine</span>
              <strong>Ready</strong>
            </div>
            <div className="readiness-row">
              <span><i /> Anomaly detection</span>
              <strong>{criticalAnomaly ? "Signal found" : "Clear"}</strong>
            </div>
            <div className="readiness-row">
              <span><i /> Forecast engine</span>
              <strong>Available</strong>
            </div>
          </div>

          <div className="readiness-footnote">
            <Database size={14} />
            <span>
              {chartData.length
                ? `${chartData.length} recent daily observations are visualized above.`
                : "Waiting for analytics data from the API."}
            </span>
          </div>
        </div>
      </section>
    </>
  )
}


function KpiCard({
  title,
  value,
  change,
  icon,
}: {
  title: string
  value: string
  change: string
  icon: ReactNode
}) {
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <span>{title}</span>
        <div className="kpi-icon">{icon}</div>
      </div>

      <strong className="kpi-value">{value}</strong>

      <div className="kpi-change positive">
        <TrendingUp size={13} />
        {change}
      </div>
    </div>
  )
}

function PageToolbar({
  eyebrow,
  title,
  description,
  onExport,
  exportLoading = false,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  onExport?: () => void
  exportLoading?: boolean
  action?: ReactNode
}) {
  return (
    <div className="page-toolbar">
      <div>
        <span className="panel-eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      <div className="page-toolbar-actions">
        {action}
        {onExport && (
          <button
            type="button"
            className="outline-button"
            onClick={onExport}
            disabled={exportLoading}
          >
            <FileText size={16} />
            {exportLoading ? "Generating PDF..." : "Export PDF report"}
          </button>
        )}
      </div>
    </div>
  )
}


function Analytics({
  data,
  loading,
}: {
  data: AnalyticsData | null
  loading: boolean
}) {
  const daily = data?.daily_revenue ?? []
  const monthly = data?.monthly_revenue ?? []
  const products = data?.top_products ?? []

  return (
    <>
      <PageToolbar
        eyebrow="BUSINESS ANALYTICS"
        title="Performance analytics"
        description="Explore revenue trends, customer economics and product contribution."
      />

      <section className="kpi-grid">
        <KpiCard
          title="Average Order Value"
          value={loading ? "Loading..." : formatCurrency(data?.kpis.average_order_value ?? 0)}
          change="Revenue / order"
          icon={<CircleDollarSign size={17} />}
        />
        <KpiCard
          title="Revenue / Customer"
          value={loading ? "Loading..." : formatCurrency(data?.kpis.revenue_per_customer ?? 0)}
          change="Identified customers"
          icon={<Users size={17} />}
        />
        <KpiCard
          title="Repeat Customer Rate"
          value={loading ? "Loading..." : `${(data?.kpis.repeat_customer_rate ?? 0).toFixed(2)}%`}
          change="Customer retention signal"
          icon={<TrendingUp size={17} />}
        />
        <KpiCard
          title="Units Sold"
          value={loading ? "Loading..." : (data?.kpis.units_sold ?? 0).toLocaleString("en-GB")}
          change="Net units"
          icon={<BarChart3 size={17} />}
        />
      </section>

      <section className="overview-main-grid">
        <div className="panel revenue-overview-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">DAILY PERFORMANCE</span>
              <h2>Actual vs expected revenue</h2>
              <p>Revenue compared with the rolling baseline returned by the analytics engine.</p>
            </div>
          </div>

          <div className="large-chart overview-revenue-chart">
            {daily.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={daily}>
                  <CartesianGrid stroke="#edf0f4" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#98a2b3" }}
                    minTickGap={30}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#98a2b3" }}
                    tickFormatter={(value: number) => `£${Math.round(Number(value) / 1000)}K`}
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      formatCurrency(Number(value ?? 0)),
                      name === "actual" ? "Actual" : "Expected",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="expected"
                    stroke="#98a2b3"
                    strokeWidth={1.6}
                    strokeDasharray="5 5"
                    fill="none"
                  />
                  <Area
                    type="monotone"
                    dataKey="actual"
                    stroke="#ff3f48"
                    strokeWidth={2.2}
                    fillOpacity={0.08}
                    fill="#ff3f48"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="overview-empty-state">
                <Activity size={20} />
                <strong>No daily analytics available</strong>
                <span>Waiting for the analytics API.</span>
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">MONTHLY PERFORMANCE</span>
              <h2>Revenue by month</h2>
              <p>Latest monthly revenue returned by the KPI engine.</p>
            </div>
          </div>

          <div className="readiness-list">
            {monthly.slice(-8).map((item) => (
              <div className="readiness-row" key={item.month}>
                <span>{item.month}</span>
                <strong>{formatCurrency(Number(item.revenue))}</strong>
              </div>
            ))}
            {!monthly.length && (
              <div className="overview-empty-state compact">
                <span>No monthly data available.</span>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="panel full-panel">
        <div className="panel-header">
          <div>
            <span className="panel-eyebrow">PRODUCT CONTRIBUTION</span>
            <h2>Top products by revenue</h2>
            <p>Highest-value products in the current dataset.</p>
          </div>
        </div>

        <div className="readiness-list">
          {products.map((item, index) => (
            <div className="readiness-row" key={`${item.product}-${index}`}>
              <span>
                <i />
                {item.product}
              </span>
              <strong>
                {formatCurrency(Number(item.revenue))} · {Number(item.share).toFixed(1)}%
              </strong>
            </div>
          ))}
          {!products.length && (
            <div className="overview-empty-state compact">
              <span>No product contribution data available.</span>
            </div>
          )}
        </div>
      </section>
    </>
  )
}

function Anomalies({
  anomalies,
  filter,
  sort,
  onFilterChange,
  onSortChange,
  onInvestigate,
}: {
  anomalies: Anomaly[]
  filter: string
  sort: string
  onFilterChange: (value: string) => void
  onSortChange: (value: string) => void
  onInvestigate: (anomaly: Anomaly) => void
}) {
  const severityRank: Record<string, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
    NORMAL: 0,
  }

  const filtered = anomalies
    .filter((item) => filter === "ALL" || item.severity === filter)
    .sort((a, b) => {
      if (sort === "date") {
        return String(b.InvoiceDate ?? "").localeCompare(
          String(a.InvoiceDate ?? ""),
        )
      }

      return (
        (severityRank[b.severity ?? "NORMAL"] ?? 0) -
        (severityRank[a.severity ?? "NORMAL"] ?? 0)
      )
    })

  const counts = anomalies.reduce<Record<string, number>>((acc, item) => {
    const key = item.severity ?? "NORMAL"
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})

  return (
    <>
      <PageToolbar
        eyebrow="DETECTION ENGINE"
        title="Anomaly center"
        description="Review unusual business events and investigate the ones that matter."
      />

      <div className="anomaly-toolbar">
        <div className="anomaly-filter-group">
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((level) => (
            <button
              key={level}
              type="button"
              className={filter === level ? "filter-chip active" : "filter-chip"}
              onClick={() => onFilterChange(level)}
            >
              {level}
              <span>{level === "ALL" ? anomalies.length : counts[level] ?? 0}</span>
            </button>
          ))}
        </div>

        <select
          className="anomaly-sort"
          value={sort}
          onChange={(event: ChangeEvent<HTMLSelectElement>) => onSortChange(event.target.value)}
          aria-label="Sort anomalies"
        >
          <option value="severity">Sort by severity</option>
          <option value="date">Sort by newest</option>
        </select>
      </div>

      <section className="anomaly-list">
        {!filtered.length ? (
          <div className="panel full-panel investigation-empty">
            <ShieldCheck size={24} />
            <strong>No anomalies found</strong>
            <span>
              There are no events matching the current severity filter.
            </span>
          </div>
        ) : (
          filtered.map((item, index) => {
            const level = item.severity ?? "LOW"
            const canInvestigate =
              level === "CRITICAL" || level === "HIGH"

            return (
              <div
                className={`anomaly-list-card ${level.toLowerCase()}`}
                key={`${item.InvoiceDate}-${index}`}
              >
                <div className={`anomaly-list-icon ${level.toLowerCase()}`}>
                  {level === "CRITICAL" || level === "HIGH" ? (
                    <AlertTriangle size={19} />
                  ) : (
                    <Activity size={19} />
                  )}
                </div>

                <div className="anomaly-list-main">
                  <div className="anomaly-list-title">
                    <h3>Revenue anomaly</h3>
                    <span className={`priority-badge ${level.toLowerCase()}`}>
                      {level}
                    </span>
                  </div>

                  <p>
                    {item.InvoiceDate?.slice(0, 10)} · Actual revenue deviated
                    materially from the expected baseline.
                  </p>

                  <div className="anomaly-inline-stats">
                    <span>
                      Actual{" "}
                      <strong>{formatCurrency(item.revenue ?? 0)}</strong>
                    </span>
                    <span>
                      Expected{" "}
                      <strong>
                        {formatCurrency(item.rolling_mean_30 ?? 0)}
                      </strong>
                    </span>
                    <span>
                      Z-score{" "}
                      <strong>{(item.z_score ?? 0).toFixed(2)}</strong>
                    </span>
                  </div>
                </div>

                <button
                  className="investigate-button compact"
                  type="button"
                  disabled={!canInvestigate}
                  onClick={() => onInvestigate(item)}
                >
                  {canInvestigate ? "Investigate" : "Review"}
                  <ChevronRight size={15} />
                </button>
              </div>
            )
          })
        )}
      </section>
    </>
  )
}

function Investigations({
  investigation,
  loading,
  error,
  onExport,
  reportLoading,
}: {
  investigation: InvestigationData | null
  loading: boolean
  error: string
  onExport: () => void
  reportLoading: boolean
}) {
  if (loading) {
    return (
      <>
        <PageToolbar
          eyebrow="ROOT CAUSE ENGINE"
          title="Investigation workspace"
          description="Running evidence-backed analysis."
        />

        <div className="panel full-panel investigation-loading">
          <Activity size={20} />
          <strong>Running investigation...</strong>
          <span>
            Computing root causes, intersections, statistical evidence and
            the AI explanation.
          </span>
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageToolbar
          eyebrow="ROOT CAUSE ENGINE"
          title="Investigation workspace"
          description="The investigation could not be completed."
        />

        <div className="panel full-panel investigation-error">
          <AlertTriangle size={20} />
          <strong>Investigation unavailable</strong>
          <span>{error}</span>
        </div>
      </>
    )
  }

  if (!investigation) {
    return (
      <>
        <PageToolbar
          eyebrow="ROOT CAUSE ENGINE"
          title="Investigation workspace"
          description="Open a critical anomaly to generate a real investigation."
        />

        <div className="panel full-panel investigation-empty">
          <Target size={22} />
          <strong>No investigation selected</strong>
          <span>
            Go to Anomalies or Overview and open a critical event. The
            investigation engine will then call the backend and generate
            evidence plus the Gemini explanation.
          </span>
        </div>
      </>
    )
  }

  const explanation =
    investigation.explanation ||
    "No AI explanation was returned by the investigation engine."

  return (
    <>
      <PageToolbar
        eyebrow="ROOT CAUSE ENGINE"
        title="Investigation workspace"
        description={`Evidence-backed analysis of the ${investigation.anomaly_date} event.`}
        onExport={onExport}
        exportLoading={reportLoading}
      />

      <section className="investigation-grid">
        <div className="panel investigation-main">
          <div className="investigation-hero">
            <div className="investigation-icon">
              <Sparkles size={22} />
            </div>

            <div>
              <span>CRITICAL EVENT</span>
              <h2>Revenue anomaly on {investigation.anomaly_date}</h2>
              <p>
                These findings are generated from the uploaded dataset by
                the investigation engine.
              </p>
            </div>
          </div>

          <div className="evidence-grid">
            <Evidence
              label="Investigation status"
              value="Completed"
              detail="Evidence pipeline executed successfully"
            />
            <Evidence
              label="Evidence records"
              value={Array.isArray(investigation.evidence)
                ? investigation.evidence.length.toLocaleString("en-GB")
                : "Available"}
              detail="Rows returned by the evidence layer"
            />
            <Evidence
              label="Root cause analysis"
              value="Computed"
              detail="Product, customer, country and time dimensions"
            />
            <Evidence
              label="AI explanation"
              value="Gemini"
              detail="Grounded in computed investigation evidence"
            />
          </div>

          <div className="intersection-box">
            <span>INVESTIGATION SUMMARY</span>
            <strong>
              The backend generated the following evidence-backed report for
              {` ${investigation.anomaly_date}`}.
            </strong>
            <p>
              The raw report and evidence are available through the API and
              the downloadable PDF report.
            </p>
          </div>
        </div>

        <div className="panel ai-panel">
          <div className="ai-panel-header">
            <Sparkles size={18} />
            <span>GEMINI AI EXPLANATION</span>
          </div>

          <h3>Evidence-backed finding</h3>

          <p className="ai-explanation">
            {explanation}
          </p>

          <div className="ai-note">
            <strong>Source</strong>
            <span>
              Investigation engine → evidence layer → Gemini
            </span>
          </div>

          <div className="ai-note">
            <strong>Important</strong>
            <span>
              The model explains computed evidence; it does not independently
              establish fraud, authenticity or business intent.
            </span>
          </div>
        </div>
      </section>

    </>
  )
}

function Evidence({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail: string
}) {
  return (
    <div className="evidence-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  )
}

type ForecastData = {
  status: string
  dataset_id: string
  model: {
    name: string
    target: string
    features: string[]
  }
  evaluation: {
    train_rows: number
    test_rows: number
    mae: number
    rmse: number
    mape: number
  }
  forecast: {
    based_on_date: string
    next_7_days_revenue: number
  }
  prediction_history: Array<{
    date: string
    actual: number
    predicted: number
  }>
  shap_importance: Array<{
    feature: string
    importance: number
  }>
}

function Forecast({ datasetId }: { datasetId: string }) {
  const [data, setData] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false

    async function loadForecast() {
      try {
        setLoading(true)
        setError("")

        const response = await fetch(
          `${API_BASE_URL}/forecast/${datasetId}`,
        )
        const result = await response.json()

        if (!response.ok) {
          throw new Error(result.detail ?? "Failed to load forecast.")
        }

        if (!cancelled) {
          setData(result as ForecastData)
        }
      } catch (error) {
        if (!cancelled) {
          setError(
            error instanceof Error
              ? error.message
              : "Unable to load forecast data.",
          )
          setData(null)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadForecast()

    return () => {
      cancelled = true
    }
  }, [datasetId])

  const predictionHistory = data?.prediction_history ?? []
  const shapImportance = data?.shap_importance ?? []

  return (
    <>
      <PageToolbar
        eyebrow="XGBOOST FORECAST"
        title="Revenue outlook"
        description="Seven-day revenue forecast generated from the live forecasting pipeline."
      />

      {error && (
        <div className="api-status error">
          <AlertTriangle size={14} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="api-status loading">
          <Activity size={14} />
          <span>Running XGBoost forecast and explanation layer...</span>
        </div>
      )}

      <section className="kpi-grid">
        <KpiCard
          title="Next 7 Days"
          value={
            loading
              ? "Loading..."
              : formatCurrency(data?.forecast?.next_7_days_revenue ?? 0)
          }
          change="Live forecast"
          icon={<TrendingUp size={17} />}
        />

        <KpiCard
          title="MAE"
          value={loading ? "Loading..." : formatCurrency(data?.evaluation?.mae ?? 0)}
          change="Test set"
          icon={<Activity size={17} />}
        />

        <KpiCard
          title="RMSE"
          value={loading ? "Loading..." : formatCurrency(data?.evaluation?.rmse ?? 0)}
          change="Test set"
          icon={<Target size={17} />}
        />

        <KpiCard
          title="MAPE"
          value={
            loading ? "Loading..." : `${(data?.evaluation?.mape ?? 0).toFixed(2)}%`
          }
          change="Test set"
          icon={<BarChart3 size={17} />}
        />
      </section>

      <section className="forecast-detail-grid">
        <div className="panel forecast-hero-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">FORECAST SIGNAL</span>
              <h2>Expected revenue for the next 7 days</h2>
              <p>
                The value below is produced directly by the backend XGBoost
                forecasting model.
              </p>
            </div>

            <span className="live-badge">
              <i />
              LIVE MODEL
            </span>
          </div>

          <div className="forecast-value-block">
            <span>Predicted revenue</span>
            <strong>
              {loading
                ? "Loading..."
                : formatCurrency(data?.forecast?.next_7_days_revenue ?? 0)}
            </strong>
            <p>
              Based on business signals available through{" "}
              <strong>{data?.forecast?.based_on_date ?? "—"}</strong>
            </p>
          </div>

          <div className="forecast-meta-grid">
            <div>
              <span>Model</span>
              <strong>{data?.model?.name ?? "—"}</strong>
            </div>
            <div>
              <span>Prediction target</span>
              <strong>{data?.model?.target ?? "—"}</strong>
            </div>
            <div>
              <span>Training rows</span>
              <strong>{data?.evaluation?.train_rows?.toLocaleString("en-GB") ?? "—"}</strong>
            </div>
            <div>
              <span>Test rows</span>
              <strong>{data?.evaluation?.test_rows?.toLocaleString("en-GB") ?? "—"}</strong>
            </div>
          </div>
        </div>

        <div className="panel forecast-quality-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">MODEL QUALITY</span>
              <h2>Validation performance</h2>
              <p>Chronological holdout evaluation from the forecasting engine.</p>
            </div>
          </div>

          <div className="quality-list">
            <div className="quality-row">
              <span>Mean Absolute Error</span>
              <strong>{loading ? "—" : formatCurrency(data?.evaluation?.mae ?? 0)}</strong>
            </div>
            <div className="quality-row">
              <span>Root Mean Square Error</span>
              <strong>{loading ? "—" : formatCurrency(data?.evaluation?.rmse ?? 0)}</strong>
            </div>
            <div className="quality-row">
              <span>Mean Absolute Percentage Error</span>
              <strong>
                {loading ? "—" : `${(data?.evaluation?.mape ?? 0).toFixed(2)}%`}
              </strong>
            </div>
          </div>

          <div className="forecast-note">
            <Sparkles size={16} />
            <span>
              Lower error values indicate tighter predictions on the held-out
              historical period. MAPE expresses average percentage error.
            </span>
          </div>
        </div>
      </section>

      <section className="forecast-visual-grid">
        <div className="panel full-panel forecast-chart-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">BACKTEST PERFORMANCE</span>
              <h2>Actual vs predicted revenue</h2>
              <p>
                Historical predictions from the chronological test set.
              </p>
            </div>

            <span className="live-badge">
              <i />
              {predictionHistory.length
                ? `${predictionHistory.length} TEST POINTS`
                : "NO TEST DATA"}
            </span>
          </div>

          <div className="large-chart forecast-prediction-chart">
            {predictionHistory.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={predictionHistory}>
                  <CartesianGrid stroke="#edf0f4" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                    minTickGap={32}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                    tickFormatter={(value: number) =>
                      `£${Math.round(Number(value) / 1000)}K`
                    }
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      formatCurrency(Number(value ?? 0)),
                      name === "actual" ? "Actual" : "Predicted",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="actual"
                    stroke="#ff3f48"
                    strokeWidth={2.4}
                    fillOpacity={0.08}
                    fill="#ff3f48"
                  />
                  <Area
                    type="monotone"
                    dataKey="predicted"
                    stroke="#98a2b3"
                    strokeWidth={1.8}
                    strokeDasharray="5 5"
                    fill="none"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="forecast-empty-chart">
                <Activity size={20} />
                <strong>No prediction history available</strong>
                <span>
                  The backend did not return historical test predictions.
                </span>
              </div>
            )}
          </div>

          <div className="chart-legend">
            <span>
              <i className="legend-dot actual" />
              Actual revenue
            </span>
            <span>
              <i className="legend-dot expected" />
              Predicted revenue
            </span>
          </div>
        </div>

        <div className="panel shap-panel">
          <div className="panel-header">
            <div>
              <span className="panel-eyebrow">MODEL EXPLAINABILITY</span>
              <h2>What drives the forecast?</h2>
              <p>Top SHAP feature contributions across the model.</p>
            </div>

            <Sparkles size={18} />
          </div>

          {shapImportance.length ? (
            <div className="shap-list">
              {shapImportance.map((item, index) => {
                const maxImportance = shapImportance[0]?.importance ?? 1
                const width = Math.max(
                  5,
                  (item.importance / maxImportance) * 100,
                )

                return (
                  <div className="shap-row" key={item.feature}>
                    <div className="shap-label">
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <strong>{item.feature}</strong>
                    </div>

                    <div className="shap-track">
                      <div
                        className="shap-fill"
                        style={{ width: `${width}%` }}
                      />
                    </div>

                    <strong className="shap-value">
                      {item.importance.toLocaleString("en-GB", {
                        maximumFractionDigits: 0,
                      })}
                    </strong>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="forecast-empty-chart">
              <Sparkles size={20} />
              <strong>SHAP explanation unavailable</strong>
              <span>
                The forecast itself is still available; no feature
                importance was returned.
              </span>
            </div>
          )}

          <div className="forecast-note">
            <Target size={15} />
            <span>
              SHAP importance measures how strongly each feature contributes
              to model predictions. It does not imply causal business impact.
            </span>
          </div>
        </div>
      </section>

      <div className="panel full-panel forecast-method-panel">
        <div className="panel-header">
          <div>
            <span className="panel-eyebrow">FORECAST PIPELINE</span>
            <h2>How this prediction is produced</h2>
            <p>
              The dashboard displays output from the real forecasting and
              explainability pipeline.
            </p>
          </div>
        </div>

        <div className="forecast-pipeline">
          <div className="pipeline-step">
            <span>01</span>
            <strong>Historical signals</strong>
            <p>Revenue, orders, customers, AOV and repeat-customer behavior.</p>
          </div>
          <ChevronRight className="pipeline-arrow" size={18} />
          <div className="pipeline-step">
            <span>02</span>
            <strong>Feature engineering</strong>
            <p>Lag features, rolling windows and calendar signals.</p>
          </div>
          <ChevronRight className="pipeline-arrow" size={18} />
          <div className="pipeline-step">
            <span>03</span>
            <strong>XGBoost model</strong>
            <p>Chronological train/test evaluation prevents future leakage.</p>
          </div>
          <ChevronRight className="pipeline-arrow" size={18} />
          <div className="pipeline-step">
            <span>04</span>
            <strong>Explain + forecast</strong>
            <p>Seven-day revenue estimate plus SHAP-based model interpretation.</p>
          </div>
        </div>
      </div>
    </>
  )
}

function SettingsPage({
  workspaceName,
  datasetName,
  investigationMode,
  criticalAlerts,
  forecastUpdates,
  message,
  onEditWorkspace,
  onChangeDataset,
  onToggleInvestigationMode,
  onToggleCriticalAlerts,
  onToggleForecastUpdates,
}: {
  workspaceName: string
  datasetName: string
  investigationMode: boolean
  criticalAlerts: boolean
  forecastUpdates: boolean
  message: string
  onEditWorkspace: () => void
  onChangeDataset: () => void
  onToggleInvestigationMode: () => void
  onToggleCriticalAlerts: () => void
  onToggleForecastUpdates: () => void
}) {
  return (
    <>
      <section className="settings-grid">
        <div className="panel settings-panel">
          <span className="panel-eyebrow">WORKSPACE</span>
          <h2>Workspace settings</h2>

          <Setting
            name="Workspace name"
            value={workspaceName}
            action="Edit"
            onClick={onEditWorkspace}
          />           <Setting
             name="Selected dataset"
             value={datasetName}
             action="Change"
             onClick={onChangeDataset}
           />

          <Setting
            name="Investigation mode"
            value="Evidence-backed analysis"
            action={investigationMode ? "On" : "Off"}
            active={investigationMode}
            onClick={onToggleInvestigationMode}
          />
        </div>

        <div className="panel settings-panel">
          <span className="panel-eyebrow">NOTIFICATIONS</span>
          <h2>Alert preferences</h2>

          <Setting
            name="Critical anomalies"
            value="Notify when critical events appear."
            action={criticalAlerts ? "On" : "Off"}
            active={criticalAlerts}
            onClick={onToggleCriticalAlerts}
          />

          <Setting
            name="Forecast updates"
            value="Receive model forecast updates."
            action={forecastUpdates ? "On" : "Off"}
            active={forecastUpdates}
            onClick={onToggleForecastUpdates}
          />
        </div>
      </section>

      {message && <div className="settings-toast">{message}</div>}
    </>
  )
}

function Setting({
  name,
  value,
  action,
  active = false,
  onClick,
}: {
  name: string
  value: string
  action: string
  active?: boolean
  onClick: () => void
}) {
  return (
    <div className="setting-row">
      <div>
        <strong>{name}</strong>
        <span>{value}</span>
      </div>

      <button
        className={`toggle ${active ? "active-toggle" : ""}`}
        onClick={onClick}
        type="button"
      >
        {action}
      </button>
    </div>
  )
}

function SystemPage() {
  const services = [
    "Data ingestion",
    "PostgreSQL",
    "KPI engine",
    "Anomaly detection",
    "Investigation engine",
    "Forecasting model",
    "AI explanation layer",
  ]

  return (
    <section className="system-overview">
      <div className="panel system-health">
        <div className="health-header">
          <div>
            <span className="panel-eyebrow">PLATFORM HEALTH</span>
            <h2>All systems operational</h2>
          </div>

          <div className="health-dot">
            <span />
            Operational
          </div>
        </div>

        <div className="service-list">
          {services.map((service) => (
            <div className="service-row" key={service}>
              <div className="service-name">
                <span />
                {service}
              </div>
              <strong>Operational</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function AboutPage() {
  return (
    <>
      <section className="about-hero">
        <div className="about-hero-copy">
          <div className="about-mark">BI</div>
          <span className="panel-eyebrow">BUSINESS INTELLIGENCE PLATFORM</span>
          <h2>Business Investigator</h2>
          <p>
            An evidence-first analytics platform designed to turn raw
            business data into clear, explainable and actionable decisions.
          </p>
        </div>

        <div className="about-hero-meta">
          <span>Project</span>
          <strong>AI Business Investigator</strong>
          <span>Focus</span>
          <strong>Anomaly detection · Root cause · Forecasting</strong>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-heading">
          <span className="panel-eyebrow">WHY THIS APPLICATION</span>
          <h2>The problem we solve</h2>
          <p>
            Business data can tell you that revenue changed, but it does not
            automatically explain what caused the change or what deserves
            attention first.
          </p>
        </div>

        <div className="about-problem-grid">
          <AboutCard
            icon={<AlertTriangle size={20} />}
            title="Find unusual events"
            text="Detect revenue anomalies using statistical baselines and anomaly scoring so important business events are surfaced instead of being hidden inside large datasets."
          />
          <AboutCard
            icon={<Target size={20} />}
            title="Explain the root cause"
            text="Break an anomaly down by product, customer, geography and time to identify the strongest contributing dimensions and their intersections."
          />
          <AboutCard
            icon={<TrendingUp size={20} />}
            title="Look ahead"
            text="Use historical business signals and an XGBoost forecasting model to estimate the next seven days of revenue and understand which features drive the prediction."
          />
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-heading">
          <span className="panel-eyebrow">PURPOSE</span>
          <h2>What Business Investigator is built for</h2>
          <p>
            The purpose is not simply to display dashboards. It is to create
            an investigation workflow that moves from a signal to evidence,
            explanation and an informed business decision.
          </p>
        </div>

        <div className="about-purpose-grid">
          <div className="panel about-detail-card">
            <div className="about-detail-icon">
              <Database size={20} />
            </div>
            <div>
              <h3>From raw data to intelligence</h3>
              <p>
                The platform accepts business transaction data, cleans and
                validates it, calculates reusable KPIs, detects unusual
                behavior, performs contribution and root-cause analysis,
                generates forecasts and presents the resulting evidence in a
                decision-oriented interface.
              </p>
            </div>
          </div>

          <div className="panel about-detail-card">
            <div className="about-detail-icon">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h3>Evidence before explanation</h3>
              <p>
                Statistical and machine-learning components produce the
                underlying evidence first. The AI explanation layer is then
                given that computed context so the final narrative remains
                grounded in measurable business signals rather than becoming
                an unsupported AI guess.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-heading">
          <span className="panel-eyebrow">INTELLIGENCE PIPELINE</span>
          <h2>How the system works</h2>
          <p>
            Each stage has a defined responsibility, with the AI layer acting
            as an explanation interface rather than the source of business
            facts.
          </p>
        </div>

        <div className="about-pipeline">
          {[
            ["01", "Data ingestion", "CSV / Excel business transaction data"],
            ["02", "Data preparation", "Cleaning, validation and structured metrics"],
            ["03", "Analytics", "KPIs, trends and customer / product economics"],
            ["04", "Anomaly detection", "Statistical baseline and anomaly severity"],
            ["05", "Investigation", "Contribution, intersections and root cause"],
            ["06", "Forecasting", "XGBoost seven-day revenue prediction"],
            ["07", "AI explanation", "Evidence-grounded business narrative"],
          ].map(([step, title, text]) => (
            <div className="about-pipeline-step" key={step}>
              <span>{step}</span>
              <div>
                <strong>{title}</strong>
                <p>{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-heading">
          <span className="panel-eyebrow">PROJECT OWNER</span>
          <h2>Built by Yash Rathi</h2>
          <p>
            A project focused on combining data analytics, machine learning
            and evidence-grounded AI into a practical business investigation
            system.
          </p>
        </div>

        <div className="about-contact-card panel">
          <div className="about-owner">
            <div className="about-owner-avatar">YR</div>
            <div>
              <span className="panel-eyebrow">CREATOR</span>
              <h3>Yash Rathi</h3>
              <p>AI Business Investigator</p>
            </div>
          </div>

          <div className="about-contact-grid">
            <a className="contact-item" href="mailto:rathiyash2005@gmail.com">
              <div className="contact-icon">
                <FileText size={17} />
              </div>
              <div>
                <span>Email</span>
                <strong>rathiyash2005@gmail.com</strong>
              </div>
              <ArrowUpRight size={15} />
            </a>

            <a className="contact-item" href="tel:+919671145652">
              <div className="contact-icon">
                <Activity size={17} />
              </div>
              <div>
                <span>Phone</span>
                <strong>+91 9671145652</strong>
              </div>
              <ArrowUpRight size={15} />
            </a>
          </div>
        </div>
      </section>

      <section className="about-final-note">
        <Sparkles size={18} />
        <div>
          <strong>The goal</strong>
          <p>
            Help a business move from “something changed” to “we know what
            changed, why it happened, what the evidence says and what to
            investigate next.”
          </p>
        </div>
      </section>

      <div className="about-footer">
        Business Investigator · Built for evidence-backed business decisions.
      </div>
    </>
  )
}

function AboutCard({
  icon,
  title,
  text,
}: {
  icon: ReactNode
  title: string
  text: string
}) {
  return (
    <div className="panel about-card">
      <div className="about-card-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  )
}

export default App
