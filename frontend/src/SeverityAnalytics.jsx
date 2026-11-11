import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CircleHelp,
  ClipboardList,
  Layers3,
    TrendingUp,

  LoaderCircle,
  RefreshCw,
  ShieldAlert,
  Activity,
} from 'lucide-react'
import './SeverityAnalytics.css'

const API_URL = 'http://127.0.0.1:8000'

const severityConfig = {
  High: {
    color: '#ef4444',
    description: 'Requires priority inspection',
  },
  Medium: {
    color: '#f59e0b',
    description: 'Requires attention',
  },
  Low: {
    color: '#22c55e',
    description: 'Monitor condition',
  },
  'Not Estimated': {
    color: '#94a3b8',
    description: 'Insufficient detection data',
  },
}

const damageClasses = ['D00', 'D20', 'D40', 'D44']

const damageClassColors = {
  D00: '#22c55e',
  D20: '#4ade80',
  D40: '#86efac',
  D44: '#a3e635',
}

const classIdMap = {
  0: 'D00',
  1: 'D20',
  2: 'D40',
  3: 'D44',
}

// Estimate severity using the largest detected bounding-box area.
function estimateSeverity(report) {
  const detections = Array.isArray(report.detections)
    ? report.detections
    : []

  if (detections.length === 0) {
    return 'Not Estimated'
  }

  const areas = detections.map((detection) =>
    Number(detection.area_percentage) || 0
  )

  const largestArea = Math.max(...areas)

  if (largestArea >= 15) return 'High'
  if (largestArea >= 5) return 'Medium'
  if (largestArea > 0) return 'Low'

  return 'Not Estimated'
}

// Read the damage class from a detection.
function getDamageClass(detection) {
  const rawClass =
    detection.class_name ??
    detection.class ??
    detection.label ??
    detection.name ??
    detection.class_id

  if (rawClass === undefined || rawClass === null) {
    return null
  }

  const value = String(rawClass).trim().toUpperCase()

  if (damageClasses.includes(value)) {
    return value
  }

  if (classIdMap[value] !== undefined) {
    return classIdMap[value]
  }

  return null
}

// Convert backend status values into readable labels.
function formatStatus(status) {
  if (!status) return 'Unknown'

  return String(status)
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function getStatusColor(status) {
  const value = status.toLowerCase()

  if (value.includes('resolved') || value.includes('verified')) {
    return '#22c55e'
  }

  if (value.includes('assigned') || value.includes('progress')) {
    return '#38bdf8'
  }

  if (value.includes('reject') || value.includes('cancel')) {
    return '#ef4444'
  }

  if (value.includes('submit') || value.includes('pending')) {
    return '#f59e0b'
  }

  return '#94a3b8'
}

export default function SeverityAnalytics({ token }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/reports?limit=100`, {
        headers: token
          ? { Authorization: `Bearer ${token}` }
          : {},
      })

      if (!response.ok) {
        throw new Error(`Could not load reports (${response.status}).`)
      }

      const data = await response.json()

      const reportList = Array.isArray(data)
        ? data
        : Array.isArray(data.reports)
          ? data.reports
          : []

      setReports(reportList)
    } catch (err) {
      console.error('Severity analytics error:', err)
      setError(err.message || 'Could not load severity analytics.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  // Count reports in each estimated severity category.
  const severityCounts = useMemo(() => {
    const counts = {
      High: 0,
      Medium: 0,
      Low: 0,
      'Not Estimated': 0,
    }

    reports.forEach((report) => {
      counts[estimateSeverity(report)] += 1
    })

    return counts
  }, [reports])

  // Count every individual detection for each damage class.
  const damageClassCounts = useMemo(() => {
    const counts = {
      D00: 0,
      D20: 0,
      D40: 0,
      D44: 0,
    }

    reports.forEach((report) => {
      const detections = Array.isArray(report.detections)
        ? report.detections
        : []

      detections.forEach((detection) => {
        const damageClass = getDamageClass(detection)

        if (damageClass) {
          counts[damageClass] += 1
        }
      })
    })

    return counts
  }, [reports])

  // Count all detections, including any class not listed in the chart.
  const totalDetections = useMemo(() => {
    return reports.reduce((total, report) => {
      const detections = Array.isArray(report.detections)
        ? report.detections
        : []

      return total + detections.length
    }, 0)
  }, [reports])

  // Count reports using their actual backend status.
  const statusCounts = useMemo(() => {
    const counts = {}

    reports.forEach((report) => {
      const rawStatus =
        report.status ??
        report.report_status ??
        report.current_status ??
        'Unknown'

      const status = formatStatus(rawStatus)

      counts[status] = (counts[status] || 0) + 1
    })

    return counts
  }, [reports])

  const totalReports = reports.length

  const maxDamageCount = Math.max(
    1,
    ...Object.values(damageClassCounts)
  )

  const statusEntries = Object.entries(statusCounts).sort(
    ([statusA], [statusB]) => statusA.localeCompare(statusB)
  )

  const maxStatusCount = Math.max(
    1,
    ...Object.values(statusCounts)
  )

  // Build the donut chart from the live severity counts.
  const severityDonutBackground = useMemo(() => {
    const entries = Object.entries(severityCounts)
    const total = totalReports

    if (total === 0) {
      return 'conic-gradient(#334155 0deg 360deg)'
    }

    let currentAngle = 0

    const segments = entries.map(([severity, count]) => {
      const angle = (count / total) * 360
      const start = currentAngle
      const end = currentAngle + angle

      currentAngle = end

      return `${severityConfig[severity].color} ${start}deg ${end}deg`
    })

    return `conic-gradient(${segments.join(', ')})`
  }, [severityCounts, totalReports])

  const cards = [
    {
      title: 'Total Reports',
      value: totalReports,
      icon: ClipboardList,
      color: '#4ade80',
      description: 'Citizen submissions',
    },
    {
      title: 'High Severity',
      value: severityCounts.High,
      icon: AlertTriangle,
      color: severityConfig.High.color,
      description: 'Priority inspection',
    },
    {
      title: 'Medium Severity',
      value: severityCounts.Medium,
      icon: TrendingUp,
      color: severityConfig.Medium.color,
      description: 'Requires attention',
    },
    {
      title: 'Low Severity',
      value: severityCounts.Low,
      icon: CheckCircle2,
      color: severityConfig.Low.color,
      description: 'Monitor condition',
    },
    {
      title: 'Not Estimated',
      value: severityCounts['Not Estimated'],
      icon: CircleHelp,
      color: severityConfig['Not Estimated'].color,
      description: 'Insufficient data',
    },
    {
      title: 'Total Detections',
      value: totalDetections,
      icon: Layers3,
      color: '#86efac',
      description: 'Detected damage instances',
    },
  ]

  if (loading) {
    return (
      <div className="severity-message">
        <LoaderCircle className="spin" size={22} />
        Loading severity analytics...
      </div>
    )
  }

  if (error) {
    return (
      <div className="severity-message severity-error">
        <AlertTriangle size={19} />
        {error}
        <button type="button" onClick={loadReports}>
          Retry
        </button>
      </div>
    )
  }

  return (
    <section className="severity-analytics-page">
      {/* Page heading */}
      <div className="severity-page-heading">
        <div>
          <span className="severity-kicker">ROAD DAMAGE INSIGHTS</span>
          <h1>Severity Overview &amp; Analytics</h1>
          <p>
            Monitor reported road damage, estimated severity and detection
            patterns.
          </p>
        </div>

        <button
          type="button"
          className="severity-refresh-button"
          onClick={loadReports}
        >
          <RefreshCw size={14} />
          REFRESH
        </button>
      </div>

      {/* Metric cards */}
      <div className="severity-cards">
        {cards.map((card) => {
          const Icon = card.icon

          return (
            <article className="severity-card" key={card.title}>
              <div
                className="severity-card-icon"
                style={{ color: card.color }}
              >
                <Icon size={19} />
              </div>

              <div className="severity-card-content">
                <span>{card.title}</span>
                <strong>{card.value}</strong>
                <small>{card.description}</small>
              </div>
            </article>
          )
        })}
      </div>

      {/* Main charts */}
      <div className="severity-charts-grid">
        {/* Severity donut */}
        <section className="severity-chart-panel severity-donut-panel">
          <div className="severity-chart-heading">
            <div>
              <span className="severity-kicker">REPORT DISTRIBUTION</span>
              <h2>Severity Breakdown</h2>
              <p>Reports grouped by estimated severity.</p>
            </div>
            <Activity size={21} />
          </div>

          <div className="severity-donut-layout">
            <div
              className="severity-donut"
              style={{ background: severityDonutBackground }}
            >
              <div className="severity-donut-center">
                <strong>{totalReports}</strong>
                <span>Total Reports</span>
              </div>
            </div>

            <div className="severity-donut-legend">
              {Object.entries(severityCounts).map(([severity, count]) => {
                const percentage =
                  totalReports > 0
                    ? Math.round((count / totalReports) * 100)
                    : 0

                return (
                  <div className="severity-legend-item" key={severity}>
                    <div className="severity-legend-label">
                      <span
                        className="severity-legend-dot"
                        style={{
                          background: severityConfig[severity].color,
                        }}
                      />
                      <span>{severity}</span>
                    </div>

                    <strong>{count}</strong>
                    <small>{percentage}%</small>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* Damage class chart */}
        <section className="severity-chart-panel">
          <div className="severity-chart-heading">
            <div>
              <span className="severity-kicker">MODEL DETECTIONS</span>
              <h2>Damage Class Distribution</h2>
              <p>Number of individual detections in each class.</p>
            </div>
            <BarChart3 size={21} />
          </div>

          <div className="severity-horizontal-chart">
            {damageClasses.map((damageClass) => {
              const count = damageClassCounts[damageClass]

              return (
                <div className="severity-bar-row" key={damageClass}>
                  <div className="severity-bar-label">
                    <span>{damageClass}</span>
                    <strong>{count}</strong>
                  </div>

                  <div className="severity-bar-track">
                    <div
                      className="severity-bar-fill"
                      style={{
                        width: `${(count / maxDamageCount) * 100}%`,
                        background: damageClassColors[damageClass],
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          <div className="severity-chart-footnote">
            Total individual detections: <strong>{totalDetections}</strong>
          </div>
        </section>
      </div>

      {/* Report status chart */}
      <section className="severity-chart-panel severity-status-panel">
        <div className="severity-chart-heading">
          <div>
            <span className="severity-kicker">WORKFLOW OVERVIEW</span>
            <h2>Report Status</h2>
            <p>Current status of citizen-submitted reports.</p>
          </div>
          <ShieldAlert size={21} />
        </div>

        {statusEntries.length > 0 ? (
          <div className="severity-horizontal-chart severity-status-chart">
            {statusEntries.map(([status, count]) => (
              <div className="severity-bar-row" key={status}>
                <div className="severity-bar-label">
                  <span>{status}</span>
                  <strong>{count}</strong>
                </div>

                <div className="severity-bar-track">
                  <div
                    className="severity-bar-fill"
                    style={{
                      width: `${(count / maxStatusCount) * 100}%`,
                      background: getStatusColor(status),
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="severity-empty-message">
            No report status information is available.
          </p>
        )}
      </section>

      {/* Important note */}
      <div className="severity-disclaimer">
        <AlertTriangle size={17} />
        <p>
          <strong>Important:</strong> Severity is a preliminary visual estimate
          based on the largest detected bounding-box area. It is not a direct
          YOLO prediction or a verified engineering assessment. Reports
          without usable detection-area data are classified as Not Estimated.
          Damage-class counts represent individual model detections, not the
          number of reports containing each class.
        </p>
      </div>
    </section>
  )
}