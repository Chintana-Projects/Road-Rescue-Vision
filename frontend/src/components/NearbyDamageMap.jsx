
import { useEffect, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './NearbyDamageMap.css'

const API_URL = 'http://127.0.0.1:8000'

const DEFAULT_CENTER = [12.9765, 77.5250]

// Only use severity when it is actually supplied by the API.
// Do not invent severity from reports with no AI detections.

function getSeverity(report) {
  const detections = Array.isArray(report.detections)
    ? report.detections
    : []

  if (detections.length === 0) return 'unknown'

  const largestArea = Math.max(
    ...detections.map(detection =>
      Number(detection.area_percentage) || 0
    )
  )

  if (largestArea >= 15) return 'high'
  if (largestArea >= 5) return 'medium'
  if (largestArea > 0) return 'low'

  return 'unknown'
}


const markerColors = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
  unknown: '#a1a1aa',
}

function createMarkerIcon(severity) {
  return L.divIcon({
    className: 'damage-map-marker-wrapper',
    html: `<div class="damage-map-marker" style="background:${markerColors[severity]}"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

// Automatically move the map to show the available reports.
function FitReports({ reports }) {
  const map = useMap()

  useEffect(() => {
    if (reports.length === 0) return

    const positions = reports.map(report => [
      report.latitude,
      report.longitude,
    ])

    if (positions.length === 1) {
      map.setView(positions[0], 15)
    } else {
      map.fitBounds(positions, { padding: [40, 40], maxZoom: 15 })
    }
  }, [reports, map])

  return null
}

function NearbyDamageMap() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function fetchReports() {
    const token = sessionStorage.getItem(
      'roadrescue_citizen_token'
    )

    if (!token) {
      setError('Please log in to view nearby road reports.')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError('')

      const response = await fetch(
        `${API_URL}/citizen/nearby-reports`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to load nearby reports.'
        )
      }

      const validReports = (data.reports || []).filter(report =>
        Number.isFinite(Number(report.latitude)) &&
        Number.isFinite(Number(report.longitude)) &&
        !(Number(report.latitude) === 0 &&
          Number(report.longitude) === 0)
      )

      setReports(validReports)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [])

  return (
    <section className="nearby-damage-section">

      <div className="nearby-damage-heading">
        <div>
          <span className="nearby-map-label">
            LIVE ROAD MONITORING
          </span>
          <h2>Nearby Road Damage</h2>
          <p>
            Explore road damage reports submitted by citizens.
          </p>
        </div>

        <button
          type="button"
          className="nearby-map-refresh"
          onClick={fetchReports}
          disabled={loading}
        >
          â†» Refresh
        </button>
      </div>

      <div className="nearby-map-summary">
        <span>
          <strong>{reports.length}</strong> mapped reports
        </span>
        <span>All citizen submissions</span>
      </div>

      {loading ? (
        <div className="nearby-map-message">
          Loading road damage locations...
        </div>
      ) : error ? (
        <div className="nearby-map-message nearby-map-error">
          {error}
          <button type="button" onClick={fetchReports}>
            Try Again
          </button>
        </div>
      ) : (
        <>
          <div className="nearby-map-container">
            <MapContainer
              center={DEFAULT_CENTER}
              zoom={13}
              scrollWheelZoom
              className="nearby-leaflet-map"
            >
              <TileLayer
  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
/>

              <FitReports reports={reports} />


              {reports.map(report => {
                const severity = getSeverity(report)


                return (
                  <Marker
  key={report.report_id}
  position={[Number(report.latitude), Number(report.longitude)]}
  icon={createMarkerIcon(severity)}
  zIndexOffset={severity === 'high' ? 1000 : 0}
>
                    <Popup>
                      <div className="damage-map-popup">
                        <h3>{report.report_id}</h3>

                        <p>
                          <strong>Severity:</strong>{' '}
                          {severity === 'unknown'
                            ? 'Not determined'
                            : severity.toUpperCase()}
                        </p>

                        <p>
                          <strong>Status:</strong>{' '}
                          {report.status || 'Unknown'}
                        </p>

                        <p>
                          <strong>Detections:</strong>{' '}
                          {report.detection_count ?? 0}
                        </p>

                        <p>
                          <strong>Description:</strong>{' '}
                          {report.description || 'No description'}
                        </p>

                        <p className="damage-map-coordinates">
                          {Number(report.latitude).toFixed(6)},{' '}
                          {Number(report.longitude).toFixed(6)}
                        </p>
                      </div>
                    </Popup>
                  </Marker>
                )
              })}
            </MapContainer>
          </div>

          <div className="nearby-map-legend">
            <span><i className="legend-dot high" /> High</span>
            <span><i className="legend-dot medium" /> Medium</span>
            <span><i className="legend-dot low" /> Low</span>
<span><i className="legend-dot unknown" /> Not Estimated</span>          </div>

          {reports.length === 0 && (
            <p className="nearby-map-empty">
              No GPS-tagged reports are available yet.
            </p>
          )}
        </>
      )}
    </section>
  )
}

export default NearbyDamageMap
