
import { useEffect, useRef, useState } from 'react'
import {
  Camera,
  MapPin,
  Send,
  Upload,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'

import './App.css'

const API_URL = 'http://127.0.0.1:8000'
const MAX_FILE_SIZE = 10 * 1024 * 1024

function CitizenReports() {
  const [file, setFile] = useState(null)
  const [description, setDescription] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)

  const [locationLoading, setLocationLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)

  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraLoading, setCameraLoading] = useState(false)

  // Duplicate report popup
  const [duplicateMatches, setDuplicateMatches] = useState([])
  const [showDuplicatePopup, setShowDuplicatePopup] = useState(false)
  const [supportLoadingId, setSupportLoadingId] = useState(null)
  const [duplicateActionMessage, setDuplicateActionMessage] = useState('')
  const [duplicateActionError, setDuplicateActionError] = useState('')

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const cameraStreamRef = useRef(null)

  async function startCamera() {
    setError('')

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access is not supported by this browser.')
      return
    }

    try {
      setCameraLoading(true)

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })

      cameraStreamRef.current = stream
      setCameraOpen(true)
    } catch (err) {
      setError(
        err.name === 'NotAllowedError'
          ? 'Camera permission denied. Please allow camera access.'
          : 'Unable to access the camera. Check your device settings.'
      )
    } finally {
      setCameraLoading(false)
    }
  }

  function stopCamera() {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      cameraStreamRef.current = null
    }

    setCameraOpen(false)
  }

  function capturePhoto() {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas || !video.videoWidth) {
      setError('Camera is not ready yet. Please try again.')
      return
    }

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const context = canvas.getContext('2d')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob((blob) => {
      if (!blob) {
        setError('Could not capture the photo. Please try again.')
        return
      }

      const photo = new File(
        [blob],
        `road_damage_${Date.now()}.jpg`,
        { type: 'image/jpeg' }
      )

      if (photo.size > MAX_FILE_SIZE) {
        setError('Captured image exceeds the 10 MB limit.')
        return
      }

      setFile(photo)
      setError('')
      setSuccess(null)
      stopCamera()
    }, 'image/jpeg', 0.90)
  }

  useEffect(() => {
    if (cameraOpen && videoRef.current && cameraStreamRef.current) {
      videoRef.current.srcObject = cameraStreamRef.current
    }
  }, [cameraOpen])

  useEffect(() => {
    return () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  function captureLocation() {
    setError('')

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.')
      return
    }

    setLocationLoading(true)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude)
        setLongitude(position.coords.longitude)
        setLocationLoading(false)
      },
      (locationError) => {
        setLocationLoading(false)
        setError(
          locationError.message ||
          'Unable to access your location. Please allow location permission.'
        )
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }
    )
  }

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0]

    if (!selectedFile) return

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(selectedFile.type)) {
      setError('Please choose a JPG, PNG or WEBP image.')
      event.target.value = ''
      return
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('Image size must be 10 MB or less.')
      event.target.value = ''
      return
    }

    setFile(selectedFile)
    setError('')
    setSuccess(null)
  }

  // Check for existing reports near the citizen's GPS location
  async function checkForDuplicates(token) {
    const response = await fetch(`${API_URL}/reports/check-duplicate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        latitude: Number(latitude),
        longitude: Number(longitude),
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Duplicate check failed.')
    }

    return data
  }

  // Support an existing road report
  async function supportExistingReport(reportId) {
    const token = sessionStorage.getItem('citizenToken')

    if (!token) {
      setDuplicateActionError('Your session has expired. Please log in again.')
      return
    }

    try {
      setSupportLoadingId(reportId)
      setDuplicateActionError('')
      setDuplicateActionMessage('')

      const response = await fetch(
        `${API_URL}/reports/${encodeURIComponent(reportId)}/support`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to support this report.')
      }

      // Don't increase the count if this citizen already supported it
      if (!data.message?.toLowerCase().includes('already')) {
        setDuplicateMatches((previousMatches) =>
          previousMatches.map((report) =>
            report.report_id === reportId
              ? {
                  ...report,
                  support_count: (report.support_count || 0) + 1,
                }
              : report
          )
        )
      }

      setDuplicateActionMessage(data.message || 'Support recorded successfully.')
    } catch (err) {
      setDuplicateActionError(
        err.message || 'Unable to support this report.'
      )
    } finally {
      setSupportLoadingId(null)
    }
  }

  // Submit the report
  // skipDuplicateCheck = true when citizen chooses to submit separately
  async function submitReport(event, skipDuplicateCheck = false) {
    if (event) {
      event.preventDefault()
    }

    setError('')
    setSuccess(null)

    if (!file) {
      setError('Please upload or capture a road damage image.')
      return
    }

    if (latitude === null || longitude === null) {
      setError('Please capture your GPS location before submitting.')
      return
    }

    const token = sessionStorage.getItem('citizenToken')

    if (!token) {
      setError('Your session has expired. Please log in again.')
      return
    }

    try {
      setSubmitting(true)

      // Check for possible duplicate reports first
      if (!skipDuplicateCheck) {
        const duplicateData = await checkForDuplicates(token)

        if (
          duplicateData.has_duplicates &&
          duplicateData.matches?.length > 0
        ) {
          setDuplicateMatches(duplicateData.matches)
          setDuplicateActionMessage('')
          setDuplicateActionError('')
          setShowDuplicatePopup(true)
          return
        }
      }

      // Continue with normal report submission
      const formData = new FormData()
      formData.append('file', file)
      formData.append('latitude', String(latitude))
      formData.append('longitude', String(longitude))
      formData.append('description', description)

      const response = await fetch(`${API_URL}/reports`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Report submission failed.'
        )
      }

      setSuccess(data)
      setFile(null)
      setDescription('')
      setLatitude(null)
      setLongitude(null)

      setShowDuplicatePopup(false)
      setDuplicateMatches([])
      setDuplicateActionMessage('')
      setDuplicateActionError('')
    } catch (err) {
      setError(err.message || 'Unable to submit report.')
    } finally {
      setSubmitting(false)
    }
  }

  function resetReportForm() {
    stopCamera()
    setFile(null)
    setDescription('')
    setLatitude(null)
    setLongitude(null)
    setError('')
    setSuccess(null)

    setDuplicateMatches([])
    setShowDuplicatePopup(false)
    setDuplicateActionMessage('')
    setDuplicateActionError('')
  }

  return (
    <div className="citizen-reports-page citizen-reports-compact">

      <div className="citizen-reports-heading">
        <div>
          <h1>Citizen Road Reports</h1>
          <p>Help make roads safer by reporting potholes and road damage.</p>
        </div>

        <div className="citizen-report-tag">
          <MapPin size={15} />
          RoadRescue Vision
        </div>
      </div>

      {success ? (
        <div className="citizen-report-success">
          <CheckCircle size={36} />
          <h2>Report Submitted Successfully!</h2>
          <p>Your road damage report has been recorded.</p>
          <h3>{success.report_id}</h3>
          <p>Status: {success.status}</p>
          <p>Detected damage: {success.detection_count}</p>

          {success.prediction_status === 'no_detections' && (
            <p>
              No damage was detected by the model in this image.
              Your report has still been submitted.
            </p>
          )}

          <button type="button" onClick={resetReportForm}>
            Submit Another Report
          </button>
        </div>
      ) : (
        <form
          className="citizen-report-form citizen-report-compact-form"
          onSubmit={submitReport}
        >

          <div className="citizen-report-grid">

            {/* LEFT: IMAGE UPLOAD AND CAMERA */}
            <div className="citizen-form-section citizen-image-section">
              <h3>
                <Camera size={18} />
                Road Damage Image
              </h3>

              <label className="citizen-upload-area citizen-upload-compact">
                <Upload size={30} />
                <span>
                  {file ? file.name : 'Choose a road image'}
                </span>
                <small>JPEG, PNG or WEBP · Maximum 10 MB</small>

                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  hidden
                />
              </label>

              <button
                type="button"
                className="citizen-camera-button"
                onClick={startCamera}
                disabled={cameraLoading || cameraOpen}
              >
                <Camera size={18} />
                {cameraLoading ? 'Opening Camera...' : 'Open Camera'}
              </button>

              {cameraOpen && (
                <div className="citizen-camera-panel">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="citizen-camera-preview"
                  />

                  <div className="citizen-camera-actions">
                    <button
                      type="button"
                      onClick={capturePhoto}
                      className="citizen-capture-button"
                    >
                      <Camera size={17} />
                      Capture Photo
                    </button>

                    <button
                      type="button"
                      onClick={stopCamera}
                      className="citizen-camera-close"
                    >
                      Close Camera
                    </button>
                  </div>
                </div>
              )}

              <canvas ref={canvasRef} hidden />

              {file && (
                <div className="citizen-selected-file">
                  <CheckCircle size={15} />
                  <span>Selected: {file.name}</span>

                  <button type="button" onClick={() => setFile(null)}>
                    Remove
                  </button>
                </div>
              )}
            </div>

            {/* RIGHT: LOCATION AND DESCRIPTION */}
            <div className="citizen-report-details">

              <div className="citizen-form-section citizen-location-section">
                <h3>
                  <MapPin size={18} />
                  Damage Location
                </h3>

                <button
                  type="button"
                  className="citizen-location-button"
                  onClick={captureLocation}
                  disabled={locationLoading}
                >
                  <MapPin size={16} />
                  {locationLoading
                    ? 'Getting Location...'
                    : 'Capture My GPS Location'}
                </button>

                {latitude !== null && longitude !== null && (
                  <div className="citizen-location-result">
                    <CheckCircle size={16} />
                    <span>
                      Latitude: {latitude.toFixed(6)}
                      <br />
                      Longitude: {longitude.toFixed(6)}
                    </span>
                  </div>
                )}
              </div>

              <div className="citizen-form-section citizen-description-section">
                <h3>Additional Description</h3>

                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Describe the road damage and nearby landmarks..."
                  rows={3}
                  maxLength={1000}
                />

                <small className="citizen-character-count">
                  {description.length}/1000 characters
                </small>
              </div>

            </div>
          </div>

          {error && (
            <div className="citizen-report-error">
              <AlertCircle size={17} />
              {error}
            </div>
          )}

          <div className="citizen-report-form-footer">
            <span className="citizen-form-hint">
              <AlertCircle size={14} />
              Image and GPS location are required.
            </span>

            <button
              type="submit"
              className="citizen-submit-button"
              disabled={submitting || cameraOpen || cameraLoading}
            >
              <Send size={16} />
              {submitting ? 'Checking / Submitting...' : 'Submit Report'}
            </button>
          </div>

          {/* POSSIBLE DUPLICATE REPORT POPUP */}
          {showDuplicatePopup && (
            <div
              onClick={(event) => {
                if (event.target === event.currentTarget) {
                  setShowDuplicatePopup(false)
                }
              }}
              style={{
                position: 'fixed',
                inset: 0,
                zIndex: 9999,
                background: 'rgba(0, 0, 0, 0.78)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                overflowY: 'auto',
              }}
            >
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="duplicate-popup-title"
                style={{
                  width: '100%',
                  maxWidth: '560px',
                  maxHeight: '85vh',
                  overflowY: 'auto',
                  background: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '16px',
                  padding: '24px',
                  color: '#e5e7eb',
                  boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
                }}
              >
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <AlertCircle
                    size={38}
                    color="#f59e0b"
                    style={{ marginBottom: '8px' }}
                  />

                  <div
  style={{
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  }}
>
  <h2>Possible Existing Report!</h2>

  <button
    type="button"
    onClick={() => setShowDuplicatePopup(false)}
    style={{
      background: 'transparent',
      border: 'none',
      color: '#fff',
      fontSize: '28px',
      cursor: 'pointer',
      padding: '0 5px',
      lineHeight: 1,
    }}
    aria-label="Close popup"
  >
    ×
  </button>
</div>

                  <p style={{ color: '#9ca3af', margin: 0 }}>
                    A road damage report has already been submitted near
                    this location. You can support an existing report or
                    submit your issue separately.
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {duplicateMatches.map((report) => (
                    <div
                      key={report.report_id}
                      style={{
                        background: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '10px',
                        padding: '15px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          gap: '10px',
                          flexWrap: 'wrap',
                        }}
                      >
                        <strong style={{ color: '#4ade80' }}>
                          {report.report_id}
                        </strong>

                        <span
                          style={{
                            color: '#d1d5db',
                            fontSize: '13px',
                          }}
                        >
                          {report.distance_m} m away
                        </span>
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: '8px',
                          margin: '12px 0',
                        }}
                      >
                        <span style={popupTagStyle}>
                          Severity: {report.severity}
                        </span>

                        <span style={popupTagStyle}>
                          Status: {report.status}
                        </span>

                        <span style={popupTagStyle}>
                          Supports: {report.support_count || 0}
                        </span>
                      </div>

                      <p
                        style={{
                          fontSize: '13px',
                          color: '#9ca3af',
                          margin: '5px 0 12px',
                        }}
                      >
                        {report.description || 'No additional description'}
                      </p>

                      <button
                        type="button"
                        onClick={() => supportExistingReport(report.report_id)}
                        disabled={supportLoadingId !== null}
                        style={{
                          width: '100%',
                          padding: '10px',
                          borderRadius: '7px',
                          border: 'none',
                          background: '#166534',
                          color: '#ffffff',
                          fontWeight: 600,
                          cursor: supportLoadingId !== null
                            ? 'not-allowed'
                            : 'pointer',
                          opacity: supportLoadingId !== null ? 0.6 : 1,
                        }}
                      >
                        {supportLoadingId === report.report_id
                          ? 'Recording Support...'
                          : 'Support Existing Report'}
                      </button>
                    </div>
                  ))}
                </div>

                {duplicateActionMessage && (
                  <p
                    style={{
                      color: '#4ade80',
                      background: 'rgba(34,197,94,0.1)',
                      padding: '10px',
                      borderRadius: '7px',
                      fontSize: '14px',
                    }}
                  >
                    <CheckCircle size={15} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                    {duplicateActionMessage}
                  </p>
                )}

                {duplicateActionError && (
                  <p
                    style={{
                      color: '#fca5a5',
                      background: 'rgba(239,68,68,0.1)',
                      padding: '10px',
                      borderRadius: '7px',
                      fontSize: '14px',
                    }}
                  >
                    <AlertCircle size={15} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                    {duplicateActionError}
                  </p>
                )}

                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    marginTop: '20px',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setShowDuplicatePopup(false)
                      submitReport(null, true)
                    }}
                    disabled={submitting || supportLoadingId !== null}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '8px',
                      border: 'none',
                      background: '#22c55e',
                      color: '#052e16',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {submitting
                      ? 'Submitting...'
                      : 'Submit as Separate Issue'}
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowDuplicatePopup(false)}
                    disabled={submitting || supportLoadingId !== null}
                    style={{
                      width: '100%',
                      padding: '11px',
                      borderRadius: '8px',
                      border: '1px solid #4b5563',
                      background: 'transparent',
                      color: '#d1d5db',
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

        </form>
      )}
    </div>
  )
}

const popupTagStyle = {
  background: '#374151',
  color: '#d1d5db',
  padding: '5px 8px',
  borderRadius: '5px',
  fontSize: '12px',
}

export default CitizenReports
