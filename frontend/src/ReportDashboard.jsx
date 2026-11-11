
import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  CalendarDays,
  CheckCircle,
  Clock,
  MapPin,
  RefreshCw,
  Search,
  ShieldCheck,
  FileText,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
const STATUSES = [
  'All',
  'Submitted',
  'Verified',
  'Assigned',
  'In Progress',
  'Resolved',
  'Rejected',
]

function formatDate(value) {
  if (!value) return 'Date unavailable'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}


function ReportDashboard({ token }) {
  const [reportImage, setReportImage] = useState('')
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [selectedReport, setSelectedReport] = useState(null)
const [expandedImage, setExpandedImage] = useState(false)
  async function fetchReports(showRefresh = false) {
    try {
      if (showRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      setError('')

      const response = await fetch(`${API_URL}/reports?limit=100`, {
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

      if (!response.ok) {
        throw new Error('Unable to fetch citizen reports.')
      }

      const data = await response.json()

      setReports(Array.isArray(data) ? data : data.reports || [])
    } catch (err) {
      setError(err.message || 'Something went wrong while loading reports.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const filteredReports = useMemo(() => {
    return reports.filter((report) => {
      const matchesStatus =
        statusFilter === 'All' || report.status === statusFilter

      const searchText = search.toLowerCase()

      const matchesSearch = [
        report.report_id,
        report.filename,
        report.description,
        report.status,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(searchText))

      return matchesStatus && matchesSearch
    })
  }, [reports, search, statusFilter])

  const statistics = useMemo(() => {
    return {
      total: reports.length,
      submitted: reports.filter((r) => r.status === 'Submitted').length,
      inProgress: reports.filter(
        (r) => r.status === 'In Progress' || r.status === 'Assigned'
      ).length,
      resolved: reports.filter((r) => r.status === 'Resolved').length,
    }
  }, [reports])


  async function viewReport(report) {
  setSelectedReport(report)
  setReportImage('')
  setError('')

  try {
    // Load report details.
    const response = await fetch(
      `${API_URL}/reports/${encodeURIComponent(report.report_id)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error('Unable to load report details.')
    }

    const data = await response.json()
    setSelectedReport(data)

    // Load the report image with staff authentication.
    const imageResponse = await fetch(
      `${API_URL}/reports/${encodeURIComponent(report.report_id)}/image`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    )

    if (!imageResponse.ok) {
      throw new Error('Unable to load report image.')
    }

    const imageBlob = await imageResponse.blob()
    const imageUrl = URL.createObjectURL(imageBlob)

    setReportImage(imageUrl)

  } catch (err) {
    setError(err.message || 'Unable to load report.')
  }
}

  function getStatusClass(status) {
    switch (status) {
      case 'Resolved':
        return 'resolved'
      case 'Verified':
        return 'verified'
      case 'In Progress':
      case 'Assigned':
        return 'progress'
      case 'Rejected':
        return 'rejected'
      default:
        return 'submitted'
    }
  }

  if (loading) {
    return (
      <div className="report-dashboard-page">
        <div className="report-dashboard-message">
          <RefreshCw size={22} className="report-dashboard-spinner" />
          <p>Loading citizen reports...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="report-dashboard-page">

      <div className="report-dashboard-heading">
        <div>
          <h1>Citizen Report Dashboard</h1>
          <p>View and track submitted road damage reports.</p>
        </div>

        <button
          type="button"
          className="report-refresh-button"
          onClick={() => fetchReports(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'report-dashboard-spinner' : ''}
          />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="report-dashboard-error">
          <AlertCircle size={17} />
          {error}
        </div>
      )}

      {/* STATISTICS */}

      <div className="report-statistics">

        <div className="report-stat-card">
          <FileText size={21} />
          <div>
            <span>Total Reports</span>
            <strong>{statistics.total}</strong>
          </div>
        </div>

        <div className="report-stat-card">
          <Clock size={21} />
          <div>
            <span>Submitted</span>
            <strong>{statistics.submitted}</strong>
          </div>
        </div>

        <div className="report-stat-card">
          <ShieldCheck size={21} />
          <div>
            <span>Assigned / In Progress</span>
            <strong>{statistics.inProgress}</strong>
          </div>
        </div>

        <div className="report-stat-card">
          <CheckCircle size={21} />
          <div>
            <span>Resolved</span>
            <strong>{statistics.resolved}</strong>
          </div>
        </div>

      </div>


      {/* SEARCH AND FILTER */}

      <div className="report-dashboard-controls">

        <div className="report-search-box">
          <Search size={17} />

          <input
            type="text"
            placeholder="Search by report ID, filename or description..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {status === 'All' ? 'All Statuses' : status}
            </option>
          ))}
        </select>

      </div>

      {/* REPORT LIST */}

      <div className="report-dashboard-list">

        <div className="report-list-heading">
          <h2>Submitted Reports</h2>
          <span>{filteredReports.length} reports</span>
        </div>

        {filteredReports.length === 0 ? (

          <div className="report-dashboard-empty">
            <FileText size={35} />
            <h3>No Reports Found</h3>
            <p>
              {reports.length === 0
                ? 'No citizen reports have been submitted yet.'
                : 'Try changing your search or status filter.'}
            </p>
          </div>

        ) : (

          filteredReports.map((report) => (

            <div className="citizen-report-card" key={report.report_id}>

              <div className="citizen-report-card-main">

                <div className="citizen-report-card-info">

                  <h3>{report.report_id}</h3>

                  <p>{report.filename}</p>

                  <div className="citizen-report-card-meta">

                    <span>
                      <CalendarDays size={14} />
                      {formatDate(report.created_at)}
                    </span>

                    <span>
                      <MapPin size={14} />
                      {report.latitude != null && report.longitude != null
                        ? `${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}`
                        : 'Location unavailable'}
                    </span>

                  </div>

                </div>

                <div className="citizen-report-card-side">

                  <span
                    className={`report-status-badge ${getStatusClass(report.status)}`}
                  >
                    {report.status || 'Submitted'}
                  </span>

                  <strong>
  {report.detection_count ?? 0} detections
</strong>

<strong style={{ color: '#16a34a' }}>
  {report.support_count ?? 0} citizen supports
</strong>

                  <button
                    type="button"
                    onClick={() => viewReport(report)}
                  >
                    View Details
                  </button>

                </div>

              </div>

            </div>

          ))

        )}

      </div>

      {/* REPORT DETAILS */}

      {selectedReport && (

        <div
          className="report-detail-overlay"
          onClick={() => setSelectedReport(null)}
        >
          <div
            className="report-detail-panel"
            onClick={(event) => event.stopPropagation()}
          >

            <div className="report-detail-heading">
              <div>
                <span>REPORT DETAILS</span>
                <h2>{selectedReport.report_id}</h2>
              </div>

              <button
                type="button"
                onClick={() => setSelectedReport(null)}
              >
                Ã—
              </button>
            </div>

<div className="report-detail-image">
  <div className="report-image-preview">
    {reportImage && (
  <img
    src={reportImage}
    alt="Citizen submitted road damage"
  />
)}
  </div>

  <div className="report-image-actions">
    <span>UPLOADED ROAD IMAGE</span>

    <button
      type="button"
      onClick={() => setExpandedImage(true)}
    >
      <Search size={15} />
      Expand Image
    </button>
  </div>
</div>

            <div className="report-detail-content">

              <div className="report-detail-item">
                <span>Status</span>
                <strong>{selectedReport.status || 'Submitted'}</strong>
              </div>

              <div className="report-detail-item">
                <span>Filename</span>
                <strong>{selectedReport.filename || 'Unavailable'}</strong>
              </div>

              <div className="report-detail-item">
                <span>Submitted On</span>
                <strong>{formatDate(selectedReport.created_at)}</strong>
              </div>

              <div className="report-detail-item">
                <span>Damage Detections</span>
                <strong>{selectedReport.detection_count ?? 0}</strong>
              </div>
              <div className="report-detail-item">
  <span>Citizen Supports</span>
  <strong>{selectedReport.support_count ?? 0}</strong>
</div>
              <div className="report-detail-item">
                <span>Latitude</span>
                <strong>{selectedReport.latitude ?? 'Unavailable'}</strong>
              </div>

              <div className="report-detail-item">
                <span>Longitude</span>
                <strong>{selectedReport.longitude ?? 'Unavailable'}</strong>
              </div>

              <div className="report-detail-description">
                <span>Description</span>
                <p>
                  {selectedReport.description || 'No description provided.'}
                </p>
              </div>

              <div className="report-detail-description">
                <span>Detected Classes</span>

                {selectedReport.detections?.length > 0 ? (
                  <ul>
                    {selectedReport.detections.map((detection, index) => (
                      <li key={index}>
                        {detection.class_name || 'Unknown'} â€”{' '}
                        {detection.confidence != null
                          ? `${(detection.confidence * 100).toFixed(1)}% confidence`
                          : 'Confidence unavailable'}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No detections recorded.</p>
                )}
              </div>

            </div>

{expandedImage && (
  <div
    className="report-image-lightbox"
    onClick={() => setExpandedImage(false)}
  >
    <div
      className="report-image-lightbox-content"
      onClick={(event) => event.stopPropagation()}
    >
      <button
        type="button"
        className="report-image-lightbox-close"
        onClick={() => setExpandedImage(false)}
      >
        Ã—
      </button>

      <img
  src={reportImage}
  alt="Expanded road damage photograph"
/>

      <p>{selectedReport.filename}</p>
    </div>
  </div>
)}

            <button
              type="button"
              className="report-detail-close"
              onClick={() => setSelectedReport(null)}
            >
              Close Details
            </button>

          </div>
        </div>

      )}

    </div>
  )
}

export default ReportDashboard
