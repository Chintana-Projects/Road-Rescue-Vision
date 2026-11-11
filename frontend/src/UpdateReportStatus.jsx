
import { useCallback, useEffect, useState } from 'react'
import {
  RefreshCw,
  ClipboardList,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

const STATUSES = [
  'Submitted',
  'Verified',
  'Assigned',
  'In Progress',
  'Resolved',
  'Rejected',
]

function UpdateReportStatus({ token }) {
  const [reports, setReports] = useState([])
  const [selectedReportId, setSelectedReportId] = useState('')
  const [newStatus, setNewStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // LOAD CITIZEN REPORTS
  const loadReports = useCallback(async () => {
    if (!token) {
      setError('Staff authentication token is missing. Please log in again.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/reports?limit=500`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          data.detail || `Could not load reports (${response.status}).`
        )
      }

      const reportList = Array.isArray(data)
        ? data
        : Array.isArray(data.reports)
          ? data.reports
          : []

      setReports(reportList)

      setSelectedReportId((currentId) => {
        if (
          currentId &&
          reportList.some((report) => report.report_id === currentId)
        ) {
          return currentId
        }

        return reportList[0]?.report_id || ''
      })
    } catch (err) {
      setError(err.message || 'Could not load citizen reports.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  // GET SELECTED REPORT
  const selectedReport = reports.find(
    (report) => report.report_id === selectedReportId
  )

  // SET DEFAULT STATUS WHEN REPORT CHANGES
  useEffect(() => {
    if (selectedReport) {
      setNewStatus(selectedReport.status || 'Submitted')
    } else {
      setNewStatus('')
    }
  }, [selectedReport])

  // UPDATE REPORT STATUS
  async function handleStatusUpdate(event) {
    event.preventDefault()

    if (!selectedReport) {
      setError('Please select a report.')
      return
    }

    if (!newStatus) {
      setError('Please select a status.')
      return
    }

    if (newStatus === selectedReport.status) {
      setError('Please select a different status.')
      return
    }

    if (!token) {
      setError('Staff authentication token is missing.')
      return
    }

    setUpdating(true)
    setError('')
    setSuccess('')

    try {
      // FastAPI expects application/x-www-form-urlencoded.
      const formData = new URLSearchParams()
      formData.append('status', newStatus)

      const response = await fetch(
        `${API_URL}/reports/${encodeURIComponent(selectedReportId)}/status`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      )

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          data.detail || `Status update failed (${response.status}).`
        )
      }

      setSuccess(
        data.message ||
          `Report ${selectedReportId} status updated to "${data.status}".`
      )

      // Refresh reports to display the latest status.
      await loadReports()

      // Display the status returned by the backend.
      setNewStatus(data.status || newStatus)
    } catch (err) {
      setError(err.message || 'Could not update report status.')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <section className="update-status-page">

      {/* PAGE HEADER */}
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-line" />
            STAFF REPORT MANAGEMENT
          </div>

          <h1>
            Update Report <span>Status</span>
          </h1>

          <p className="page-description">
            Review citizen-submitted reports and update their progress.
            Every status change is recorded in the citizen's progress timeline.
          </p>
        </div>

        <button
          type="button"
          className="history-refresh-button"
          onClick={loadReports}
          disabled={loading || updating}
        >
          <RefreshCw
            size={14}
            className={loading ? 'spin' : ''}
          />
          {loading ? 'LOADING...' : 'REFRESH REPORTS'}
        </button>
      </div>

      {/* REPORT MANAGEMENT PANEL */}
      <div
        className="panel"
        style={{ padding: '24px', marginTop: '24px' }}
      >
        <div className="panel-heading">
          <div className="panel-heading-icon">
            <ClipboardList size={18} />
          </div>

          <div>
            <span className="panel-kicker">REPORT MANAGEMENT</span>
            <h2>Select a citizen report</h2>
            <p>
              Choose a report to view its current status and update it.
            </p>
          </div>
        </div>

        {/* ERROR MESSAGE */}
        {error && (
          <div className="error-message" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* SUCCESS MESSAGE */}
        {success && (
          <div className="status-success-message" role="status">
            <CheckCircle2 size={18} />
            <span>{success}</span>
          </div>
        )}

        {/* LOADING STATE */}
        {loading ? (
          <div className="history-empty">
            <RefreshCw className="spin" size={22} />
            <span>Loading citizen reports...</span>
          </div>
        ) : reports.length === 0 ? (
          /* EMPTY STATE */
          <div className="history-empty">
            <ClipboardList size={28} />
            <strong>No citizen reports found</strong>
            <span>
              Reports submitted by citizens will appear here.
            </span>
          </div>
        ) : (
          <form onSubmit={handleStatusUpdate}>

            {/* REPORT SELECTOR */}
            <div className="status-form-group">
              <label htmlFor="status-report-select">
                SELECT REPORT
              </label>

              <select
                id="status-report-select"
                value={selectedReportId}
                onChange={(event) => {
                  setSelectedReportId(event.target.value)
                  setError('')
                  setSuccess('')
                }}
                disabled={updating}
              >
                {reports.map((report) => (
                  <option
                    key={report.report_id}
                    value={report.report_id}
                  >
                    {report.report_id} — {report.filename} — {report.status}
                  </option>
                ))}
              </select>
            </div>

            {selectedReport && (
              <>

                {/* REPORT INFORMATION */}
                <div className="status-report-details">

                  <div className="history-detail-grid">
                    <div>
                      <span>REPORT ID</span>
                      <strong>{selectedReport.report_id}</strong>
                    </div>
                  </div>

                  <div className="history-detail-grid">
                    <div>
                      <span>FILE NAME</span>
                      <strong>{selectedReport.filename || 'Not available'}</strong>
                    </div>
                  </div>

                  <div className="history-detail-grid">
                    <div>
                      <span>SUBMITTED ON</span>
                      <strong>
                        {selectedReport.created_at
                          ? new Date(
                              selectedReport.created_at
                            ).toLocaleString()
                          : 'Not available'}
                      </strong>
                    </div>
                  </div>

                  <div className="history-detail-grid">
                    <div>
                      <span>DETECTIONS</span>
                      <strong>
                        {selectedReport.detection_count ?? 0}
                      </strong>
                    </div>
                  </div>

                </div>

                {/* CURRENT STATUS */}
                <div className="current-status-card">

                  <div className="current-status-heading">
                    <Clock size={17} />
                    <strong>CURRENT STATUS</strong>
                  </div>

                  <span className="history-status">
                    {selectedReport.status || 'Submitted'}
                  </span>

                </div>

                {/* NEW STATUS SELECTOR */}
                <div className="status-form-group new-status-group">
                  <label htmlFor="new-report-status">
                    SELECT NEW STATUS
                  </label>

                  <select
                    id="new-report-status"
                    value={newStatus}
                    onChange={(event) => {
                      setNewStatus(event.target.value)
                      setError('')
                      setSuccess('')
                    }}
                    disabled={updating}
                  >
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </div>

                {/* UPDATE BUTTON */}
                <button
                  type="submit"
                  className="analyze-button status-update-button"
                  disabled={
                    updating ||
                    !newStatus ||
                    newStatus === selectedReport.status
                  }
                >
                  {updating ? (
                    <>
                      <RefreshCw className="spin" size={17} />
                      UPDATING STATUS...
                    </>
                  ) : (
                    <>
                      <ShieldCheck size={17} />
                      UPDATE REPORT STATUS
                    </>
                  )}
                </button>

              </>
            )}
          </form>
        )}
      </div>

      {/* INFORMATION PANEL */}
      <div
        className="panel status-information-panel"
        style={{ padding: '20px', marginTop: '20px' }}
      >
        <div className="status-information-content">
          <ShieldCheck size={20} />

          <div>
            <strong>Status updates are recorded</strong>

            <p>
              When you change a report's status, RoadRescue saves the previous
              status, new status and timestamp. The citizen can view this
              change in the Report Progress Timeline.
            </p>
          </div>
        </div>
      </div>

    </section>
  )
}

export default UpdateReportStatus
