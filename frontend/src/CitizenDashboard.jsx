
import { useEffect, useState } from 'react'
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
  AlertCircle,
  MapPin,
  CalendarDays,
} from 'lucide-react'

import './App.css'
const API_URL = 'http://127.0.0.1:8000'


// --------------------------------------------------
// ANNOTATED IMAGE POPUP
// --------------------------------------------------

function AnnotatedReportImage({ reportId }) {
  const [isOpen, setIsOpen] = useState(false)
  const [imageUrl, setImageUrl] = useState(null)
  const [imageLoading, setImageLoading] = useState(false)
  const [imageError, setImageError] = useState(false)

  useEffect(() => {
    if (!isOpen) return

    let cancelled = false
    let objectUrl = null

    async function fetchAnnotatedImage() {
      const token = sessionStorage.getItem(
        'roadrescue_citizen_token'
      )

      setImageLoading(true)
      setImageError(false)
      setImageUrl(null)

      try {
        const response = await fetch(
          `${API_URL}/citizen/reports/${encodeURIComponent(reportId)}/annotated-image`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error('Image unavailable')
        }

        const blob = await response.blob()
        objectUrl = URL.createObjectURL(blob)

        if (!cancelled) {
          setImageUrl(objectUrl)
        }
      } catch (error) {
        if (!cancelled) {
          setImageError(true)
        }
      } finally {
        if (!cancelled) {
          setImageLoading(false)
        }
      }
    }

    fetchAnnotatedImage()

    return () => {
      cancelled = true

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [isOpen, reportId])

  // CLOSE POPUP USING ESCAPE KEY

  useEffect(() => {
    if (!isOpen) return

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    window.addEventListener('keydown', handleEscape)

    return () => {
      window.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  return (
    <>
      <button
        type="button"
        className="see-image-btn"
        onClick={() => setIsOpen(true)}
      >
        See Image
      </button>

      {isOpen && (
        <div
          className="image-modal-overlay"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="image-modal"
            role="dialog"
            aria-modal="true"
            aria-label="YOLO annotated report image"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="image-modal-header">
              <div>
                <h3>YOLO Damage Detection</h3>
                <p>Annotated road damage report</p>
              </div>

              <button
                type="button"
                className="image-modal-close"
                onClick={() => setIsOpen(false)}
                aria-label="Close image"
              >
                Ã—
              </button>
            </div>

            <div className="image-modal-content">
              {imageLoading && (
                <p>Loading annotated image...</p>
              )}

              {imageError && (
                <p>Unable to load annotated image.</p>
              )}

              {imageUrl && (
                <img
                  src={imageUrl}
                  alt={`YOLO damage detection for report ${reportId}`}
                />
              )}
            </div>

            <p className="image-modal-report-id">
              Report ID: {reportId}
            </p>
          </div>
        </div>
      )}
    </>
  )
}


// --------------------------------------------------
// REPORT PROGRESS TIMELINE
// --------------------------------------------------

function ReportTimeline({ reportId }) {
  const [isOpen, setIsOpen] = useState(false)
  const [timeline, setTimeline] = useState([])
  const [currentStatus, setCurrentStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchTimeline() {
    const token = sessionStorage.getItem(
      'roadrescue_citizen_token'
    )

    if (!token) {
      setError('Please log in again.')
      return
    }

    try {
      setLoading(true)
      setError('')

      const response = await fetch(
        `${API_URL}/citizen/reports/${encodeURIComponent(reportId)}/timeline`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to load report timeline.'
        )
      }

      setTimeline(data.timeline || [])
      setCurrentStatus(data.current_status || '')

    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  async function toggleTimeline() {
    const opening = !isOpen
    setIsOpen(opening)

    if (opening) {
      await fetchTimeline()
    }
  }

  function formatTimelineDate(dateString) {
    if (!dateString) return 'Date unavailable'

    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="report-timeline-container">

      <button
        type="button"
        className="report-timeline-toggle"
        onClick={toggleTimeline}
      >
        <Clock size={16} />
        {isOpen ? 'Hide Progress' : 'Track Progress'}
        <span>{isOpen ? 'âˆ’' : '+'}</span>
      </button>

      {isOpen && (
        <div className="report-timeline-content">

          <div className="report-timeline-heading">
  <h4>Report Timeline</h4>

  {currentStatus && (
    <span className="timeline-current-status">
      {currentStatus}
    </span>
  )}
</div>

          {loading && (
            <p className="timeline-message">
              Loading report progress...
            </p>
          )}

          {error && (
            <div className="timeline-error">
              <p>{error}</p>
              <button
                type="button"
                onClick={fetchTimeline}
              >
                Try Again
              </button>
            </div>
          )}

          {!loading && !error && timeline.length > 0 && (
            <div className="horizontal-timeline-scroll">

              <div className="horizontal-timeline">

                {timeline.map((item, index) => {
                  const isLatest = index === timeline.length - 1

                  return (
                    <div
                      className="horizontal-timeline-step"
                      key={`${item.changed_at}-${index}`}
                    >

                      <div className="horizontal-timeline-marker">

                        <div
                          className={`horizontal-timeline-dot ${
                            isLatest ? 'current' : 'completed'
                          }`}
                        >
                          <CheckCircle size={17} />
                        </div>

                        {index !== timeline.length - 1 && (
                          <div className="horizontal-timeline-line" />
                        )}

                      </div>

                      <div className="horizontal-timeline-details">

                        <h5 className={isLatest ? 'active-step' : ''}>
                          {item.new_status}
                        </h5>

                        {item.old_status && (
                          <p>
                            From {item.old_status}
                          </p>
                        )}

                        <span>
                          {formatTimelineDate(item.changed_at)}
                        </span>

                        {isLatest && (
                          <small>Latest Update</small>
                        )}

                      </div>

                    </div>
                  )
                })}

              </div>

            </div>
          )}

          {!loading && !error && timeline.length === 0 && (
            <p className="timeline-message">
              No progress history available yet.
            </p>
          )}

        </div>
      )}

    </div>
  )
}


// --------------------------------------------------
// CITIZEN DASHBOARD
// --------------------------------------------------

function CitizenDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAllReports, setShowAllReports] = useState(false)

  async function fetchDashboard() {
    const token = sessionStorage.getItem(
      'roadrescue_citizen_token'
    )

    if (!token) {
      setError('Please log in to view your dashboard.')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError('')

      const response = await fetch(
        `${API_URL}/citizen/dashboard`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Unable to load dashboard.'
        )
      }

      setDashboard(data)

    } catch (err) {
      setError(err.message || 'Something went wrong.')

    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [])

  // FORMAT DATE

  function formatDate(dateString) {
    if (!dateString) return 'Date unavailable'

    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  // REPORT STATUS

  function getStatusClass(status) {
    switch (status?.toLowerCase()) {
      case 'resolved':
        return 'resolved'

      case 'rejected':
        return 'rejected'

      case 'verified':
      case 'assigned':
      case 'in progress':
        return 'progress'

      default:
        return 'pending'
    }
  }

  // LOADING SCREEN

  if (loading) {
    return (
      <div className="citizen-dashboard-loading">
        <RefreshCw className="loading-icon" size={28} />
        <p>Loading your dashboard...</p>
      </div>
    )
  }

  // ERROR SCREEN

  if (error) {
    return (
      <div className="citizen-dashboard-error">
        <AlertCircle size={24} />
        <p>{error}</p>

        <button onClick={fetchDashboard}>
          Try Again
        </button>
      </div>
    )
  }

  if (!dashboard) return null

  // DASHBOARD STATISTICS

  const statistics = [
    {
      title: 'Total Reports',
      value: dashboard.total_reports ?? 0,
      icon: FileText,
      className: 'total',
    },
    {
      title: 'Pending Reports',
      value: dashboard.pending_reports ?? 0,
      icon: Clock,
      className: 'pending',
    },
    {
      title: 'Resolved Reports',
      value: dashboard.resolved_reports ?? 0,
      icon: CheckCircle,
      className: 'resolved',
    },
    {
      title: 'Rejected Reports',
      value: dashboard.rejected_reports ?? 0,
      icon: XCircle,
      className: 'rejected',
    },
  ]

  const recentReports = dashboard.recent_reports || []

  const visibleReports = showAllReports
    ? recentReports
    : recentReports.slice(0, 2)

  return (
    <div className="citizen-dashboard">

      {/* DASHBOARD HEADING */}

      <div className="citizen-dashboard-heading">
        <div>
          <span className="citizen-dashboard-label">
            ROADRESCUE VISION
          </span>

          <h1>Welcome Back!</h1>

          <p>
            Track your road damage reports and monitor their progress.
          </p>
        </div>

        <button
          className="citizen-refresh-button"
          onClick={fetchDashboard}
          title="Refresh dashboard"
        >
          <RefreshCw size={17} />
          Refresh
        </button>
      </div>


      {/* STATISTICS */}

      <div className="citizen-statistics-grid">

        {statistics.map((stat) => {
          const Icon = stat.icon

          return (
            <div
              className={`citizen-stat-card ${stat.className}`}
              key={stat.title}
            >
              <div className="citizen-stat-icon">
                <Icon size={23} />
              </div>

              <div>
                <p>{stat.title}</p>
                <h2>{stat.value}</h2>
              </div>
            </div>
          )
        })}

      </div>


      {/* RECENT REPORTS */}
            {/* NEARBY ROAD DAMAGE MAP */}


      {/* RECENT REPORTS */}

      <div className="citizen-recent-reports">

        <div className="citizen-section-heading">
          <div>
            <h2>Recent Reports</h2>
            <p>Your latest road damage submissions</p>
          </div>

          {recentReports.length > 2 && (
            <button
              type="button"
              className="citizen-view-all-button"
              onClick={() => setShowAllReports(!showAllReports)}
            >
              {showAllReports ? 'Show Less' : 'View All Reports'}
            </button>
          )}
        </div>

        {recentReports.length === 0 ? (

          <div className="citizen-empty-reports">
            <FileText size={40} />
            <h3>No Reports Yet</h3>

            <p>
              You haven't submitted any road damage reports.
            </p>
          </div>

        ) : (

          <div className="citizen-report-list">

            {visibleReports.map((report) => (

              <div
                className="citizen-dashboard-report"
                key={report.report_id}
              >

                <div className="citizen-report-main">

                  <div className="citizen-report-icon">
                    <FileText size={22} />
                  </div>

                  <div className="citizen-report-info">

                    <h3>{report.report_id}</h3>

                    <p>{report.filename}</p>

                    <div className="citizen-report-meta">

                      <span>
                        <CalendarDays size={14} />
                        {formatDate(report.created_at)}
                      </span>

                      <span>
                        <MapPin size={14} />

                        {report.latitude != null &&
                        report.longitude != null
                          ? 'Location available'
                          : 'Location unavailable'}
                      </span>

                    </div>

                    {/* SEE ANNOTATED IMAGE BUTTON */}

                   <div className="report-actions-row">

  <AnnotatedReportImage
    reportId={report.report_id}
  />

  <ReportTimeline
    reportId={report.report_id}
  />

</div>

                  </div>

                </div>


                {/* REPORT STATUS AND DETECTIONS */}

                <div className="citizen-report-right">

                  <span
                    className={`citizen-status ${getStatusClass(report.status)}`}
                  >
                    {report.status}
                  </span>

                  <p>
                    {report.detection_count ?? 0} damage detections
                  </p>

                </div>

              </div>

            ))}

          </div>

        )}

      </div>

    </div>
  )
}

export default CitizenDashboard
