
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
  // Form states
  const [file, setFile] = useState(null)
  const [description, setDescription] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)

  // Loading and response states
  const [locationLoading, setLocationLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)

  // Camera states and references
  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraLoading, setCameraLoading] = useState(false)

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const cameraStreamRef = useRef(null)

  // Start device camera
  async function startCamera() {
    setError('')

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access is not supported by this browser.')
      return
    }

    try {
      setCameraLoading(true)

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
        },
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

  // Stop camera
  function stopCamera() {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      cameraStreamRef.current = null
    }

    setCameraOpen(false)
  }

  // Capture image from live camera
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
      stopCamera()
    }, 'image/jpeg', 0.90)
  }

  // Attach camera stream to video element
  useEffect(() => {
    if (cameraOpen && videoRef.current && cameraStreamRef.current) {
      videoRef.current.srcObject = cameraStreamRef.current
    }
  }, [cameraOpen])

  // Stop camera when component unmounts
  useEffect(() => {
    return () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  // Capture GPS location
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

  // Select image from device
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

  // Submit citizen report
  async function submitReport(event) {
    event.preventDefault()

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

    const formData = new FormData()

    formData.append('file', file)
    formData.append('latitude', latitude)
    formData.append('longitude', longitude)
    formData.append('description', description)

    try {
      setSubmitting(true)

      const response = await fetch(`${API_URL}/reports`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Report submission failed.')
      }

      setSuccess(data)
      setFile(null)
      setDescription('')
      setLatitude(null)
      setLongitude(null)
    } catch (err) {
      setError(err.message || 'Unable to submit report.')
    } finally {
      setSubmitting(false)
    }
  }

  // Reset form for another report
  function resetReportForm() {
    stopCamera()
    setFile(null)
    setDescription('')
    setLatitude(null)
    setLongitude(null)
    setError('')
    setSuccess(null)
  }

  return (
    <div className="citizen-reports-page">

      <div className="citizen-reports-heading">
        <div>
          <h1>Citizen Road Reports</h1>
          <p>
            Report potholes and road damage directly to the
            RoadRescue system.
          </p>
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

          <button
            type="button"
            onClick={resetReportForm}
          >
            Submit Another Report
          </button>
        </div>

      ) : (

        <form
          className="citizen-report-form"
          onSubmit={submitReport}
        >

          {/* ROAD DAMAGE IMAGE */}

          <div className="citizen-form-section">
            <h3>
              <Camera size={18} />
              Road Damage Image
            </h3>

            <div className="citizen-upload-actions">

              <label className="citizen-upload-area">
                <Upload size={28} />

                <span>
                  {file ? file.name : 'Choose an image from your device'}
                </span>

                <small>JPEG, PNG or WEBP · Max 10 MB</small>

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
                <Camera size={20} />

                {cameraLoading
                  ? 'Opening Camera...'
                  : 'Open Camera'}
              </button>

            </div>

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
                <button
                  type="button"
                  onClick={() => setFile(null)}
                >
                  Remove
                </button>
              </div>
            )}

          </div>

          {/* GPS LOCATION */}

          <div className="citizen-form-section">
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

          {/* DESCRIPTION */}

          <div className="citizen-form-section">
            <h3>Additional Description</h3>

            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the road damage and nearby landmarks..."
              rows={4}
              maxLength={1000}
            />
          </div>

          {/* ERROR MESSAGE */}

          {error && (
            <div className="citizen-report-error">
              <AlertCircle size={17} />
              {error}
            </div>
          )}

          {/* SUBMIT BUTTON */}

          <button
            type="submit"
            className="citizen-submit-button"
            disabled={submitting || cameraOpen || cameraLoading}
          >
            <Send size={16} />

            {submitting
              ? 'Submitting Report...'
              : 'Submit Road Damage Report'}
          </button>

        </form>
      )}

    </div>
  )
}

export default CitizenReports
