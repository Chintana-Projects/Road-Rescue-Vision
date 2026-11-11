import UpdateReportStatus from './UpdateReportStatus'
import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowUpRight, CheckCircle2, ChevronDown,
  CircleHelp, CloudUpload, FileImage, Gauge, HardHat, History,
  Image as ImageIcon, LoaderCircle, MapPin, ScanSearch, ShieldCheck,
  Trash2, Upload, Wifi, X, LayoutDashboard, ClipboardList, LogOut,
} from 'lucide-react'
import CitizenNotifications from './CitizenNotifications'
import './App.css'
import ReportDashboard from './ReportDashboard'
import SeverityAnalytics from './SeverityAnalytics'
import StaffLogin from './StaffLogin'
import CitizenReports from './CitizenReports'
import CitizenDashboard from './CitizenDashboard'
import NearbyDamageMap from './components/NearbyDamageMap'
const API_URL = 'http://127.0.0.1:8000'
const MAX_FILE_SIZE = 10 * 1024 * 1024

const classDescriptions = {
  D00: 'Longitudinal crack',
  D20: 'Alligator crack',
  D40: 'Pothole',
  D44: 'Other road damage',
}

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [loading, setLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [annotatedUrl, setAnnotatedUrl] = useState('')
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [apiStatus, setApiStatus] = useState('checking')

  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [selectedInspection, setSelectedInspection] = useState(null)
  const [historyActionId, setHistoryActionId] = useState(null)
  const [historyMenuOpen, setHistoryMenuOpen] = useState(false)
  const [historyFilter, setHistoryFilter] = useState('all')
  const [historySort, setHistorySort] = useState('newest')
  const [historySearch, setHistorySearch] = useState('')
  const [citizenReportsMenuOpen, setCitizenReportsMenuOpen] = useState(false)
  const [activeView, setActiveView] = useState('analyzer')

  const [staffToken, setStaffToken] = useState(
    () => sessionStorage.getItem('roadrescue_staff_token') || ''
  )

  const [staffUsername, setStaffUsername] = useState(
    () => sessionStorage.getItem('roadrescue_staff_username') || ''
  )

  const [citizenToken, setCitizenToken] = useState(
    () => sessionStorage.getItem('roadrescue_citizen_token') || ''
  )

  const [citizenUsername, setCitizenUsername] = useState(
    () => sessionStorage.getItem('roadrescue_citizen_username') || ''
  )

  const [citizenName, setCitizenName] = useState(
    () => sessionStorage.getItem('roadrescue_citizen_name') || ''
  )

  const detections = result?.detections ?? []

  const damageCounts = useMemo(
    () =>
      detections.reduce((counts, detection) => {
        const name = detection.class_name || 'Unknown'
        counts[name] = (counts[name] || 0) + 1
        return counts
      }, {}),
    [detections]
  )

  // STAFF LOGIN
  function handleStaffLogin(token, username) {
    sessionStorage.removeItem('roadrescue_citizen_token')
    sessionStorage.removeItem('roadrescue_citizen_username')
    sessionStorage.removeItem('roadrescue_citizen_name')

    sessionStorage.removeItem('citizenToken')
    sessionStorage.removeItem('citizenUsername')
    sessionStorage.removeItem('citizenName')

    setCitizenToken('')
    setCitizenUsername('')
    setCitizenName('')

    sessionStorage.setItem('roadrescue_staff_token', token)
    sessionStorage.setItem('roadrescue_staff_username', username)

    setStaffToken(token)
    setStaffUsername(username)
    setActiveView('analyzer')
  }

  function handleStaffLogout() {
    sessionStorage.removeItem('roadrescue_staff_token')
    sessionStorage.removeItem('roadrescue_staff_username')

    setStaffToken('')
    setStaffUsername('')
  }

  // CITIZEN LOGIN
  function handleCitizenLogin(token, username, fullName) {
    sessionStorage.removeItem('roadrescue_staff_token')
    sessionStorage.removeItem('roadrescue_staff_username')

    setStaffToken('')
    setStaffUsername('')

    sessionStorage.setItem('roadrescue_citizen_token', token)
    sessionStorage.setItem('roadrescue_citizen_username', username)
    sessionStorage.setItem('roadrescue_citizen_name', fullName)

    // Keep aliases for citizen components that read these keys.
    sessionStorage.setItem('citizenToken', token)
    sessionStorage.setItem('citizenUsername', username)
    sessionStorage.setItem('citizenName', fullName)

    setCitizenToken(token)
    setCitizenUsername(username)
    setCitizenName(fullName)

    setActiveView('citizen-dashboard')
  }

  function handleCitizenLogout() {
    sessionStorage.removeItem('roadrescue_citizen_token')
    sessionStorage.removeItem('roadrescue_citizen_username')
    sessionStorage.removeItem('roadrescue_citizen_name')

    sessionStorage.removeItem('citizenToken')
    sessionStorage.removeItem('citizenUsername')
    sessionStorage.removeItem('citizenName')

    setCitizenToken('')
    setCitizenUsername('')
    setCitizenName('')
    setActiveView('analyzer')
  }

  // FILTER AND SORT INSPECTION HISTORY
  const filteredHistory = useMemo(() => {
    const filtered = history.filter((item) => {
      const matchesFilter =
        historyFilter === 'all' ||
        (historyFilter === 'damage' && Number(item.detection_count) > 0) ||
        (historyFilter === 'no-damage' && Number(item.detection_count) === 0)

      const searchText = historySearch.trim().toLowerCase()

      const matchesSearch =
        !searchText ||
        item.filename?.toLowerCase().includes(searchText) ||
        item.detections?.some((detection) =>
          detection.class_name?.toLowerCase().includes(searchText)
        ) ||
        String(item.id).includes(searchText)

      return matchesFilter && matchesSearch
    })

    return [...filtered].sort((a, b) => {
      switch (historySort) {
        case 'oldest':
          return new Date(a.created_at) - new Date(b.created_at)

        case 'most':
          return Number(b.detection_count) - Number(a.detection_count)

        case 'fewest':
          return Number(a.detection_count) - Number(b.detection_count)

        default:
          return new Date(b.created_at) - new Date(a.created_at)
      }
    })
  }, [history, historyFilter, historySearch, historySort])

  const historyStats = useMemo(
    () => ({
      total: history.length,
      damage: history.filter(
        (item) => Number(item.detection_count) > 0
      ).length,
      clear: history.filter(
        (item) => Number(item.detection_count) === 0
      ).length,
    }),
    [history]
  )

  // CHECK BACKEND STATUS
  useEffect(() => {
    let active = true

    async function checkApi() {
      try {
        const response = await fetch(`${API_URL}/health`)

        if (!response.ok) throw new Error('API unavailable')

        const data = await response.json()

        if (active) {
          setApiStatus(data.model_loaded ? 'online' : 'model-missing')
        }
      } catch {
        if (active) setApiStatus('offline')
      }
    }

    checkApi()

    const interval = window.setInterval(checkApi, 15000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    if (activeView === 'analyzer') {
      document.getElementById('analyzer')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }

    if (activeView === 'results') {
      document.getElementById('results')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }
  }, [activeView])

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview)
      if (annotatedUrl) URL.revokeObjectURL(annotatedUrl)
    },
    [preview, annotatedUrl]
  )

  function clearResult() {
    setResult(null)
    setError('')

    setAnnotatedUrl((current) => {
      if (current) URL.revokeObjectURL(current)
      return ''
    })
  }

  function selectFile(selectedFile) {
    if (!selectedFile) return

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(selectedFile.type)) {
      setError('Please choose a JPG, PNG, or WEBP image.')
      return
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('Image size must be 10 MB or less.')
      return
    }

    clearResult()

    setPreview((current) => {
      if (current) URL.revokeObjectURL(current)
      return URL.createObjectURL(selectedFile)
    })

    setFile(selectedFile)
    setError('')
  }

  function removeFile() {
    clearResult()

    setPreview((current) => {
      if (current) URL.revokeObjectURL(current)
      return ''
    })

    setFile(null)
  }

  // LOAD STAFF INSPECTION HISTORY
  async function loadHistory() {
    setHistoryLoading(true)
    setHistoryError('')

    try {
      const response = await fetch(`${API_URL}/history?limit=50`)

      if (!response.ok) {
        throw new Error(`History API (${response.status})`)
      }

      const data = await response.json()

      setHistory(
        Array.isArray(data.inspections) ? data.inspections : []
      )
    } catch (err) {
      setHistoryError(err.message || 'Could not load inspection history.')
    } finally {
      setHistoryLoading(false)
    }
  }

  // EXPORT HISTORY AS CSV
  function exportHistoryCSV() {
    if (filteredHistory.length === 0) {
      setHistoryError('There are no inspection records to export.')
      return
    }

    const headers = [
      'Inspection ID',
      'Filename',
      'Date',
      'Image Width',
      'Image Height',
      'Confidence Threshold (%)',
      'Detection Count',
      'Damage Classes',
      'Prediction Status',
    ]

    const escapeCSV = (value) => {
      let text = String(value ?? '')

      if (/^[=+\-@]/.test(text)) {
        text = `'${text}`
      }

      return `"${text.replace(/"/g, '""')}"`
    }

    const rows = filteredHistory.map((item) => [
      item.id,
      item.filename,
      new Date(item.created_at).toLocaleString(),
      item.image_width,
      item.image_height,
      (Number(item.confidence_threshold) * 100).toFixed(0),
      item.detection_count,
      [...new Set((item.detections || []).map((d) => d.class_name))].join(', '),
      item.prediction_status,
    ])

    const csvContent = [
      headers.map(escapeCSV).join(','),
      ...rows.map((row) => row.map(escapeCSV).join(',')),
    ].join('\n')

    const blob = new Blob(['\uFEFF' + csvContent], {
      type: 'text/csv;charset=utf-8;',
    })

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = 'RoadRescue_Inspection_History.csv'

    document.body.appendChild(link)
    link.click()
    link.remove()

    URL.revokeObjectURL(url)
  }

  // RUN ROAD DAMAGE ANALYSIS
  async function analyzeRoad() {
    if (!file) {
      setError('Upload a road image before starting the analysis.')
      return
    }

    setLoading(true)
    setError('')
    clearResult()

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
        `${API_URL}/predict?conf=0.10`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        const details = await response.json().catch(() => ({}))

        throw new Error(
          `Prediction API (${response.status}): ${details.detail || 'Request failed.'}`
        )
      }

      const data = await response.json()

      setResult(data)
      await loadHistory()

      const visualData = new FormData()
      visualData.append('file', file)

      try {
        const visualResponse = await fetch(
          `${API_URL}/predict/visual?conf=0.10`,
          {
            method: 'POST',
            body: visualData,
          }
        )

        if (!visualResponse.ok) {
          const details = await visualResponse.json().catch(() => ({}))

          throw new Error(
            `Visual API (${visualResponse.status}): ${details.detail || 'Request failed.'}`
          )
        }

        const imageBlob = await visualResponse.blob()

        setAnnotatedUrl(URL.createObjectURL(imageBlob))
      } catch (visualError) {
        console.error('Annotated image request failed:', visualError)

        setError(
          `Predictions succeeded, but the annotated image failed: ${visualError.message}`
        )
      }
    } catch (err) {
      console.error('Road analysis failed:', err)

      setError(err.message || 'Cannot connect to the RoadRescue API.')
    } finally {
      setLoading(false)
    }
  }

  // DOWNLOAD PDF REPORT
  async function downloadReport() {
    if (!file || !result) {
      setError('Run the road analysis before downloading a report.')
      return
    }

    setReportLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
       `${API_URL}/predict/report?conf=0.10`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        const details = await response.json().catch(() => ({}))

        throw new Error(
          `Report API (${response.status}): ${details.detail || 'Could not generate the PDF report.'}`
        )
      }

      const pdfBlob = await response.blob()
      const downloadUrl = URL.createObjectURL(pdfBlob)
      const link = document.createElement('a')

      const safeName = file.name
        .replace(/\.[^/.]+$/, '')
        .replace(/[^a-z0-9_-]/gi, '_')

      link.href = downloadUrl
      link.download = `roadrescue-report-${safeName || 'inspection'}.pdf`

      document.body.appendChild(link)
      link.click()
      link.remove()

      URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      console.error('PDF report download failed:', err)

      setError(err.message || 'Could not download the PDF report.')
    } finally {
      setReportLoading(false)
    }
  }

  // VIEW INSPECTION DETAILS
  async function viewInspection(inspectionId) {
    setHistoryActionId(inspectionId)
    setHistoryError('')

    try {
      const response = await fetch(
        `${API_URL}/history/${inspectionId}`
      )

      if (!response.ok) {
        throw new Error(`Could not load inspection (${response.status})`)
      }

      setSelectedInspection(await response.json())
    } catch (err) {
      setHistoryError(err.message || 'Could not load inspection details.')
    } finally {
      setHistoryActionId(null)
    }
  }

  function closeInspection() {
    setSelectedInspection(null)
    setHistoryError('')
  }

  // DELETE INSPECTION
  async function removeInspection(inspectionId) {
    if (!window.confirm('Delete this inspection from history?')) return

    setHistoryActionId(inspectionId)
    setHistoryError('')

    try {
      const response = await fetch(
        `${API_URL}/history/${inspectionId}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error(`Could not delete inspection (${response.status})`)
      }

      setHistory((current) =>
        current.filter((item) => item.id !== inspectionId)
      )

      if (selectedInspection?.id === inspectionId) {
        setSelectedInspection(null)
      }
    } catch (err) {
      setHistoryError(err.message || 'Could not delete inspection.')
    } finally {
      setHistoryActionId(null)
    }
  }

  function openHistory(filter) {
    setHistoryFilter(filter)
    setActiveView('history')
    setHistoryMenuOpen(true)
    setSelectedInspection(null)
  }

  const apiLabel = {
    checking: 'CHECKING API',
    online: 'AI SERVICE ONLINE',
    'model-missing': 'MODEL NOT LOADED',
    offline: 'API OFFLINE',
  }[apiStatus]

  // ==================================================
  // CITIZEN PORTAL
  // ==================================================

  if (citizenToken && !staffToken) {
    return (
      <div className="citizen-portal-shell">

        <aside className="citizen-portal-sidebar">

          <div className="citizen-portal-brand">
            <div className="citizen-portal-brand-icon">
              <HardHat size={23} />
            </div>

            <div>
              <strong>ROADRESCUE</strong>
              <small>CITIZEN PORTAL</small>
            </div>
          </div>

          <div className="citizen-portal-user">
            <div className="citizen-portal-avatar">
              {(citizenName || citizenUsername || 'C')
                .charAt(0)
                .toUpperCase()}
            </div>

            <div>
              <strong>{citizenName || citizenUsername}</strong>
              <small>REGISTERED CITIZEN</small>
            </div>
          </div>

          <div className="citizen-portal-nav-label">
            MAIN MENU
          </div>

          <button
            type="button"
            className={`citizen-portal-nav-item ${
              activeView === 'citizen-dashboard' ? 'active' : ''
            }`}
            onClick={() => setActiveView('citizen-dashboard')}
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>

          <button
            type="button"
            className={`citizen-portal-nav-item ${
              activeView === 'citizen-reports' ? 'active' : ''
            }`}
            onClick={() => setActiveView('citizen-reports')}
          >
            <ClipboardList size={18} />
            <span>Report Road Damage</span>
          </button>
                    <button
            type="button"
            className={`citizen-portal-nav-item ${
              activeView === 'nearby-map' ? 'active' : ''
            }`}
            onClick={() => setActiveView('nearby-map')}
          >
            <MapPin size={18} />
            <span>Nearby Damage Map</span>
          </button>

          <div className="citizen-portal-sidebar-bottom">
            <div className="citizen-portal-help">
              <ShieldCheck size={17} />
              <span>Community-powered road monitoring</span>
            </div>

            <button
              type="button"
              className="citizen-portal-logout"
              onClick={handleCitizenLogout}
            >
              <LogOut size={17} />
              LOG OUT
            </button>
          </div>

        </aside>

        <main className="citizen-portal-main">

          <header className="citizen-portal-topbar">
            <div>
              <span>ROADRESCUE VISION</span>

              <strong>
  {activeView === 'citizen-reports'
    ? ' / REPORT ROAD DAMAGE'
    : activeView === 'nearby-map'
      ? ' / NEARBY DAMAGE MAP'
      : ' / CITIZEN DASHBOARD'}
</strong>
            </div>

            <div className="citizen-portal-topbar-user">
  <CitizenNotifications token={citizenToken} />
  <span className="citizen-portal-online-dot" />
  CITIZEN ACCOUNT
</div>
          </header>

          <div className="citizen-portal-content">

  {activeView === 'citizen-reports' ? (
    <CitizenReports />
  ) : activeView === 'nearby-map' ? (
    <NearbyDamageMap />
  ) : (
    <CitizenDashboard />
  )}

</div>

        </main>

      </div>
    )
  }

  // ==================================================
  // LOGIN / ROLE SELECTION
  // ==================================================

  if (!staffToken && !citizenToken) {
    return (
      <StaffLogin
        onLogin={handleStaffLogin}
        onCitizenLogin={handleCitizenLogin}
      />
    )
  }

  // ==================================================
  // STAFF PORTAL
  // ==================================================

  return (
    <div className="app-shell">

      <aside className="sidebar">

        <a
          className="brand"
          href="#home"
          aria-label="RoadRescue Vision home"
          onClick={() => setActiveView('analyzer')}
        >
          <span className="brand-mark">
            <HardHat size={22} />
          </span>

          <span className="brand-copy">
            <strong>ROADRESCUE</strong>
            <small>VISION PLATFORM</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`nav-item ${
            activeView === 'analyzer' ? 'active' : ''
          }`}
          type="button"
          onClick={() => setActiveView('analyzer')}
        >
          <ScanSearch size={17} />
          <span>Road Analyzer</span>
          {activeView === 'analyzer' && (
            <span className="nav-indicator" />
          )}
        </button>



        <div className="sidebar-history">
          <button
            className={`nav-item history-nav-trigger ${
              activeView === 'history' ? 'active' : ''
            }`}
            type="button"
            aria-expanded={historyMenuOpen}
            onClick={() => {
              setHistoryMenuOpen((open) => !open)
              setActiveView('history')
              setHistoryFilter('all')
              setSelectedInspection(null)
            }}
          >
            <History size={17} />
            <span>Inspection History</span>

            <ChevronDown
              className={`history-chevron ${
                historyMenuOpen ? 'is-open' : ''
              }`}
              size={15}
            />
          </button>

          {historyMenuOpen && (
            <div className="history-submenu">

              <button
                type="button"
                className={historyFilter === 'all' ? 'selected' : ''}
                onClick={() => openHistory('all')}
              >
                All Inspections <span>{history.length}</span>
              </button>

              <button
                type="button"
                className={historyFilter === 'damage' ? 'selected' : ''}
                onClick={() => openHistory('damage')}
              >
                Damage Detected
                <span>
                  {history.filter(
                    (item) => Number(item.detection_count) > 0
                  ).length}
                </span>
              </button>

              <button
                type="button"
                className={historyFilter === 'no-damage' ? 'selected' : ''}
                onClick={() => openHistory('no-damage')}
              >
                No Damage Detected
                <span>
                  {history.filter(
                    (item) => Number(item.detection_count) === 0
                  ).length}
                </span>
              </button>
            </div>
          )}
        </div>


<div className="sidebar-citizen-reports">

  <button
    className={`nav-item ${
  activeView === 'report-dashboard' ||
  activeView === 'severity-analytics'
    ? 'active'
    : ''
}`}
    type="button"
    aria-expanded={citizenReportsMenuOpen}
    onClick={() => {
      setCitizenReportsMenuOpen((open) => !open)
      setActiveView('report-dashboard')
    }}
  >
    <MapPin size={17} />
    <span>Citizen Road Reports</span>

    <ChevronDown
      className={`history-chevron ${
        citizenReportsMenuOpen ? 'is-open' : ''
      }`}
      size={15}
    />
  </button>

  {citizenReportsMenuOpen && (
  <div className="history-submenu">

    <button
      type="button"
      className={
        activeView === 'report-dashboard' ? 'selected' : ''
      }
      onClick={() => setActiveView('report-dashboard')}
    >
      View Submitted Reports
    </button>

    <button
      type="button"
      className={
        activeView === 'severity-analytics' ? 'selected' : ''
      }
      onClick={() => setActiveView('severity-analytics')}
    >
      Severity Overview & Analytics
    </button>

  </div>
)}


</div>
<div className="sidebar-citizen-reports">
  <button
    className={`nav-item ${
      activeView === 'update-report-status' ? 'active' : ''
    }`}
    type="button"
    onClick={() => setActiveView('update-report-status')}
  >
    <ClipboardList size={17} />
    <span>Update Report Status</span>

    {activeView === 'update-report-status' && (
      <span className="nav-indicator" />
    )}
  </button>
</div>




        <div className="sidebar-bottom">



          <div className="sidebar-footer">
            <ShieldCheck size={15} />
            AI-assisted inspection
          </div>

          <div className="staff-account">

            <div className="staff-account-info">
              <ShieldCheck size={17} />

              <div>
                <strong>{staffUsername}</strong>
                <small>AUTHORIZED STAFF</small>
              </div>
            </div>

            <button
              type="button"
              className="staff-logout-button"
              onClick={handleStaffLogout}
            >
              LOG OUT
            </button>

          </div>

        </div>

      </aside>

      <main className="main-content" id="home">

        <header className="topbar">

          <div className="breadcrumbs">
            <span>WORKSPACE</span>
            <b>/</b>

            <strong>
              {activeView === 'history'
                ? 'INSPECTION HISTORY'
                : activeView === 'results'
                  ? 'ANALYSIS RESULTS'
                  : activeView === 'citizen-reports'
                    ? 'SUBMIT A REPORT'
                   : activeView === 'report-dashboard'
  ? 'CITIZEN REPORT DASHBOARD'
  : activeView === 'severity-analytics'
    ? 'SEVERITY OVERVIEW & ANALYTICS'
  : activeView === 'update-report-status'
    ? 'UPDATE REPORT STATUS'
    : 'ROAD ANALYZER'}
            </strong>
          </div>

          <div className="topbar-right">
            <span className="environment-tag">
              <span className="status-dot" />
              LOCAL ENVIRONMENT
            </span>

            <span className="topbar-divider" />
            <span className="avatar">RR</span>
          </div>

        </header>

        {/* STAFF VIEW ROUTING */}

        {activeView === 'citizen-reports' ? (
  <CitizenReports />

) : activeView === 'report-dashboard' ? (
  <ReportDashboard token={staffToken} />
) : activeView === 'severity-analytics' ? (
  <SeverityAnalytics token={staffToken} />
) : activeView === 'update-report-status' ? (
  <UpdateReportStatus token={staffToken} />

) : activeView !== 'history' ? (
          <>

            <section className="page-heading" id="analyzer">

              <div>
                <div className="eyebrow">
                  <span className="eyebrow-line" />
                  ROAD INFRASTRUCTURE INTELLIGENCE
                </div>

                <h1>
                  Road Damage <span>Analyzer</span>
                </h1>

                <p className="page-description">
                  Computer vision for identifying road-surface defects
                  and supporting smarter inspection workflows.
                </p>
              </div>

              <div className="model-chip">
                <span className="chip-pulse" />
                <Activity size={15} />
                YOLOv8
                <span className="chip-divider">/</span>
                OBJECT DETECTION
              </div>

            </section>

            <section className="metrics-grid" aria-label="Platform information">

              <article className="metric-card">
                <div className="metric-top">
                  <span>MODEL STATUS</span>
                  <Wifi size={16} />
                </div>

                <div className="metric-value">
                  <span className={`status-dot ${
                    apiStatus !== 'online' ? 'muted' : ''
                  }`} />

                  {apiStatus === 'online'
                    ? 'Ready to analyze'
                    : apiStatus === 'offline'
                      ? 'API disconnected'
                      : apiStatus === 'model-missing'
                        ? 'Model unavailable'
                        : 'Checking connection'}
                </div>

                <p>Local AI inference service</p>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <span>SUPPORTED CLASSES</span>
                  <ScanSearch size={16} />
                </div>

                <div className="metric-number">04</div>
                <p>D00 <i /> D20 <i /> D40 <i /> D44</p>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <span>UPLOAD LIMIT</span>
                  <CloudUpload size={16} />
                </div>

                <div className="metric-number">
                  10 <small>MB</small>
                </div>

                <p>JPG, PNG and WEBP images</p>
              </article>

            </section>

            <div className="workspace-grid">

              <section className="panel upload-panel">

                <div className="panel-heading">
                  <div className="panel-heading-icon">
                    <Upload size={17} />
                  </div>

                  <div>
                    <span className="panel-kicker">INPUT SOURCE</span>
                    <h2>Upload road image</h2>
                    <p>Choose a clear image of the road surface.</p>
                  </div>

                  <span className="step-number">01</span>
                </div>

                {!preview ? (
                  <label
                    className={`dropzone ${
                      dragging ? 'dragging' : ''
                    }`}
                    onDragOver={(event) => {
                      event.preventDefault()
                      setDragging(true)
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => {
                      event.preventDefault()
                      setDragging(false)
                      selectFile(event.dataTransfer.files?.[0])
                    }}
                  >
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(event) => {
                        selectFile(event.target.files?.[0])
                        event.target.value = ''
                      }}
                      hidden
                    />

                    <span className="upload-icon">
                      <CloudUpload size={25} />
                    </span>

                    <strong>Drop road image to inspect</strong>
                    <span className="dropzone-subtitle">
                      or browse files from your device
                    </span>

                    <span className="browse-button">
                      Select image <ArrowUpRight size={14} />
                    </span>

                    <span className="file-hint">
                      JPG / PNG / WEBP <i /> MAX 10 MB
                    </span>
                  </label>

                ) : (
                  <div className="preview-card">

                    <div className="preview-image-wrap">
                      <img
                        src={preview}
                        alt="Selected road for analysis"
                      />

                      <span className="preview-badge">
                        <span className="tiny-green-dot" />
                        SOURCE IMAGE
                      </span>

                      <button
                        className="remove-image"
                        onClick={removeFile}
                        title="Remove image"
                        aria-label="Remove image"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <div className="file-details">
                      <FileImage size={18} />

                      <div className="file-name">
                        <strong>{file.name}</strong>
                        <span>
                          {(file.size / (1024 * 1024)).toFixed(2)} MB
                          Â· Ready for analysis
                        </span>
                      </div>

                      <span className="file-ready">
                        <CheckCircle2 size={14} />
                        READY
                      </span>
                    </div>

                  </div>
                )}



                {error && (
                  <div className="error-message" role="alert">
                    <AlertTriangle size={16} />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  className="analyze-button"
                  onClick={analyzeRoad}
                  disabled={!file || loading}
                >
                  {loading ? (
                    <>
                      <LoaderCircle className="spin" size={18} />
                      ANALYZING IMAGE...
                    </>
                  ) : (
                    <>
                      <ScanSearch size={17} />
                      RUN DAMAGE ANALYSIS
                      <ArrowUpRight size={16} />
                    </>
                  )}
                </button>

                <p className="privacy-note">
                  <ShieldCheck size={14} />
                  Image is processed by your locally running API.
                </p>

              </section>

              {/* ANALYSIS RESULTS */}

              <section className="panel results-panel" id="results">

                <div className="panel-heading results-heading">

                  <div className="panel-heading-icon">
                    <Gauge size={17} />
                  </div>

                  <div>
                    <span className="panel-kicker">MODEL OUTPUT</span>
                    <h2>Inspection results</h2>
                    <p>Predictions generated by the trained model.</p>
                  </div>

                  {result ? (
                    <span className="result-count">
                      {result.detection_count} FOUND
                    </span>
                  ) : (
                    <span className="step-number">02</span>
                  )}

                </div>

                {!result && !loading && (
                  <div className="empty-results">

                    <div className="empty-art">
                      <div className="empty-art-grid" />
                      <ScanSearch size={36} />
                      <span className="scan-corner top-left" />
                      <span className="scan-corner top-right" />
                      <span className="scan-corner bottom-left" />
                      <span className="scan-corner bottom-right" />
                    </div>

                    <span className="empty-kicker">
                      AWAITING IMAGE INPUT
                    </span>

                    <h3>Ready for inspection</h3>

                    <p>
                      Upload a road image and run the model to view
                      detected regions, damage classes and confidence scores.
                    </p>

                    <div className="empty-checklist">
                      <span><CheckCircle2 size={14} /> Image preview</span>
                      <span><CheckCircle2 size={14} /> AI predictions</span>
                      <span><CheckCircle2 size={14} /> Annotated output</span>
                    </div>

                  </div>
                )}

                {loading && (
                  <div className="loading-state">
                    <div className="loading-ring">
                      <LoaderCircle className="spin" size={32} />
                    </div>

                    <span className="empty-kicker">
                      COMPUTER VISION IN PROGRESS
                    </span>

                    <strong>Analyzing road image</strong>

                    <p>
                      Running object detection and preparing the visual result.
                    </p>
                  </div>
                )}

                {result && !loading && (
                  <div className="result-content">

                    <div className={`status-banner ${
                      detections.length
                        ? 'has-detections'
                        : 'no-detections'
                    }`}>
                      {detections.length ? (
                        <AlertTriangle size={18} />
                      ) : (
                        <CheckCircle2 size={18} />
                      )}

                      <div>
                        <strong>
                          {detections.length
                            ? 'Potential damage detected'
                            : 'No detections at this threshold'}
                        </strong>

                        <span>
                          {detections.length
                            ? `${detections.length} prediction(s) require visual verification.`
                            : 'This does not prove the road is damage-free.'}
                        </span>
                      </div>
                    </div>

                    <div className="annotated-section">

                      <div className="subsection-heading">
                        <strong>DETECTION OVERLAY</strong>
                        <span>ANNOTATED MODEL OUTPUT</span>
                      </div>

                      {annotatedUrl ? (
                        <img
                          className="annotated-image"
                          src={annotatedUrl}
                          alt="Road image with model-predicted bounding boxes"
                        />
                      ) : (
                        <div className="annotated-fallback">
                          <ImageIcon size={21} />
                          <span>
                            Annotated image unavailable.
                            Detection details are shown below.
                          </span>
                        </div>
                      )}

                    </div>

                    <button
                      className="analyze-button report-download-button"
                      onClick={downloadReport}
                      disabled={!file || reportLoading}
                      type="button"
                    >
                      {reportLoading ? (
                        <>
                          <LoaderCircle className="spin" size={18} />
                          GENERATING PDF REPORT...
                        </>
                      ) : (
                        <>
                          <FileImage size={17} />
                          DOWNLOAD PDF REPORT
                          <ArrowUpRight size={16} />
                        </>
                      )}
                    </button>

                    <div className="detection-summary">
                      <div>
                        <span>TOTAL DETECTIONS</span>
                        <strong>
                          {detections.length.toString().padStart(2, '0')}
                        </strong>
                      </div>

                      <div>
                        <span>DAMAGE CLASSES</span>
                        <strong>
                          {Object.keys(damageCounts).length
                            .toString()
                            .padStart(2, '0')}
                        </strong>
                      </div>
                    </div>

                    <div className="detection-list-heading">
                      <strong>DETECTION DETAILS</strong>
                      <span>{detections.length} RESULT(S)</span>
                    </div>

                    {detections.length === 0 ? (
                      <p className="no-detections-text">
                        No boxes passed the selected confidence threshold.
                        Try a lower threshold, but verify any predictions carefully.
                      </p>
                    ) : (
                      <div className="detection-list">

                        {detections.map((detection, index) => (
                          <article
                            className="detection-item"
                            key={`${detection.class_id}-${index}`}
                          >
                            <div className="detection-class-icon">
                              <MapPin size={16} />
                            </div>

                            <div className="detection-info">
                              <strong>{detection.class_name}</strong>

                              <span>
                                {classDescriptions[detection.class_name] ||
                                  'Road damage class'}
                              </span>

                              <small>
                                Box: ({detection.box.x1}, {detection.box.y1})
                                â€“ ({detection.box.x2}, {detection.box.y2})
                              </small>
                            </div>

                            <div className="detection-confidence">
                              <strong>
                                {(detection.confidence * 100).toFixed(2)}%
                              </strong>
                              <span>CONFIDENCE</span>
                            </div>
                          </article>
                        ))}

                      </div>
                    )}

                    <div className="class-breakdown">

                      <div className="subsection-heading">
                        <strong>CLASS DISTRIBUTION</strong>
                        <span>DETECTED OBJECTS</span>
                      </div>

                      {Object.entries(damageCounts).length ? (
                        Object.entries(damageCounts).map(([name, count]) => (
                          <div className="breakdown-row" key={name}>
                            <span>{name}</span>

                            <div className="breakdown-track">
                              <i
                                style={{
                                  width: `${(count / detections.length) * 100}%`,
                                }}
                              />
                            </div>

                            <strong>{count}</strong>
                          </div>
                        ))
                      ) : (
                        <span className="breakdown-empty">
                          No detected classes to display.
                        </span>
                      )}

                    </div>

                    <div className="result-disclaimer">
                      <AlertTriangle size={15} />
                      <span>
                        {result.note} This prototype is not a verified
                        road-safety assessment and must not replace an
                        on-site inspection.
                      </span>
                    </div>

                  </div>
                )}

              </section>

            </div>

          </>
        ) : (
          // INSPECTION HISTORY PAGE

          <section className="history-page">

            <div className="page-heading history-page-heading">

              <div>
                <div className="eyebrow">
                  <span className="eyebrow-line" />
                  SAVED INSPECTION RECORDS
                </div>

                <h1>
                  Inspection <span>History</span>
                </h1>

                <p className="page-description">
                  Browse, filter and review previously analyzed road images.
                </p>
              </div>

              <div className="history-heading-actions">

                <button
                  className="history-export-button"
                  type="button"
                  onClick={exportHistoryCSV}
                  disabled={filteredHistory.length === 0}
                >
                  <FileImage size={14} />
                  EXPORT CSV
                </button>

                <button
                  className="history-refresh-button"
                  type="button"
                  onClick={loadHistory}
                  disabled={historyLoading}
                >
                  {historyLoading ? (
                    <>
                      <LoaderCircle className="spin" size={14} />
                      REFRESHING...
                    </>
                  ) : (
                    'â†» REFRESH'
                  )}
                </button>

              </div>

            </div>

            <div className="history-search">
              <ScanSearch size={18} />

              <input
                type="text"
                placeholder="Search by filename, damage class or inspection ID..."
                value={historySearch}
                onChange={(event) =>
                  setHistorySearch(event.target.value)
                }
                aria-label="Search inspection history"
              />

              {historySearch && (
                <button
                  type="button"
                  onClick={() => setHistorySearch('')}
                  aria-label="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            <div className="history-sort">
              <label htmlFor="history-sort-select">SORT BY</label>

              <select
                id="history-sort-select"
                value={historySort}
                onChange={(event) =>
                  setHistorySort(event.target.value)
                }
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="most">Most Detections</option>
                <option value="fewest">Fewest Detections</option>
              </select>
            </div>

            <div
              className="history-filter-tabs"
              role="group"
              aria-label="Filter inspection history"
            >
              <button
                type="button"
                className={historyFilter === 'all' ? 'selected' : ''}
                onClick={() => setHistoryFilter('all')}
              >
                All Inspections <span>{history.length}</span>
              </button>

              <button
                type="button"
                className={historyFilter === 'damage' ? 'selected' : ''}
                onClick={() => setHistoryFilter('damage')}
              >
                Damage Detected
                <span>
                  {history.filter(
                    (item) => Number(item.detection_count) > 0
                  ).length}
                </span>
              </button>

              <button
                type="button"
                className={historyFilter === 'no-damage' ? 'selected' : ''}
                onClick={() => setHistoryFilter('no-damage')}
              >
                No Damage Detected
                <span>
                  {history.filter(
                    (item) => Number(item.detection_count) === 0
                  ).length}
                </span>
              </button>
            </div>

            {historyError && (
              <div className="error-message" role="alert">
                <AlertTriangle size={16} />
                <span>{historyError}</span>
              </div>
            )}

            {historyLoading && history.length === 0 ? (
              <div className="history-empty">
                Loading saved inspections...
              </div>
            ) : filteredHistory.length === 0 ? (
              <div className="history-empty">
                <FileImage size={28} />
                <strong>No records in this category</strong>

                <span>
                  {history.length === 0
                    ? 'Run an image analysis to create your first history record.'
                    : 'Choose another history filter to see more records.'}
                </span>
              </div>
            ) : (
              <div className="history-list">

                {filteredHistory.map((item) => (
                  <article className="history-item" key={item.id}>

                    <div className="history-item-icon">
                      <FileImage size={19} />
                    </div>

                    <div className="history-item-main">

                      <span className="history-record-id">
                        INSPECTION #{item.id}
                      </span>

                      <strong title={item.filename}>
                        {item.filename}
                      </strong>

                      <span>
                        {new Date(item.created_at).toLocaleString()}
                      </span>

                      <div className="history-item-meta">

                        <span
                          className={`history-status ${
                            Number(item.detection_count) > 0
                              ? 'detected'
                              : 'clear'
                          }`}
                        >
                          {Number(item.detection_count) > 0
                            ? 'DAMAGE DETECTED'
                            : 'NO DAMAGE DETECTED'}
                        </span>

                        <span>
                          {item.detection_count} detection(s)
                        </span>

                      </div>

                      {Number(item.detection_count) > 0 && (
                        <div className="history-class-tags">
                          {[
                            ...new Set(
                              (item.detections || []).map(
                                (detection) => detection.class_name
                              )
                            ),
                          ].map((className) => (
                            <span key={className}>
                              {className}
                            </span>
                          ))}
                        </div>
                      )}

                    </div>

                    <div className="history-item-actions">

                      <button
                        type="button"
                        onClick={() => viewInspection(item.id)}
                        disabled={historyActionId === item.id}
                      >
                        {historyActionId === item.id
                          ? 'LOADING...'
                          : 'VIEW'}
                      </button>

                      <button
                        type="button"
                        className="history-delete-button"
                        onClick={() => removeInspection(item.id)}
                        disabled={historyActionId === item.id}
                        aria-label={`Delete inspection ${item.id}`}
                      >
                        <Trash2 size={14} />
                        DELETE
                      </button>

                    </div>

                  </article>
                ))}

              </div>
            )}

            {selectedInspection && (
              <div className="history-detail" key={selectedInspection.id}>

                <div className="subsection-heading">

                  <strong>
                    INSPECTION #{selectedInspection.id}
                  </strong>

                  <button
                    type="button"
                    className="history-close-button"
                    onClick={closeInspection}
                  >
                    <X size={14} />
                    CLOSE
                  </button>

                </div>

                <div className="history-detail-grid">

                  <div>
                    <span>FILE</span>
                    <strong>{selectedInspection.filename}</strong>
                  </div>

                  <div>
                    <span>DATE</span>
                    <strong>
                      {new Date(
                        selectedInspection.created_at
                      ).toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>IMAGE DIMENSIONS</span>
                    <strong>
                      {selectedInspection.image_width} Ã—
                      {selectedInspection.image_height}
                    </strong>
                  </div>

                  <div>
                    <span>CONFIDENCE THRESHOLD</span>
                    <strong>
                      {(selectedInspection.confidence_threshold * 100).toFixed(0)}%
                    </strong>
                  </div>

                  <div>
                    <span>DETECTIONS</span>
                    <strong>
                      {selectedInspection.detection_count}
                    </strong>
                  </div>

                </div>

                {selectedInspection.detections?.length ? (
                  <div className="detection-list">

                    {selectedInspection.detections.map(
                      (detection, index) => (
                        <article
                          className="detection-item"
                          key={`${detection.class_id}-${index}`}
                        >
                          <div className="detection-class-icon">
                            <MapPin size={16} />
                          </div>

                          <div className="detection-info">
                            <strong>{detection.class_name}</strong>

                            <span>
                              {classDescriptions[detection.class_name] ||
                                'Road damage class'}
                            </span>
                          </div>

                          <div className="detection-confidence">
                            <strong>
                              {(detection.confidence * 100).toFixed(2)}%
                            </strong>
                            <span>CONFIDENCE</span>
                          </div>

                        </article>
                      )
                    )}

                  </div>
                ) : (
                  <p>
                    No detections were recorded for this inspection.
                  </p>
                )}

              </div>
            )}

          </section>
        )}

        <footer className="page-footer">
          <span>
            ROADRESCUE VISION <i /> DEEP LEARNING PROTOTYPE
          </span>

          <span>
            INSPECTION SUPPORT <i /> NOT SAFETY CERTIFICATION
          </span>
        </footer>

      </main>

    </div>
  )
}

export default App
