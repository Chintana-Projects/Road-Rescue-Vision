
import { useEffect, useState } from 'react'
import { Bell, CheckCheck, RefreshCw, X } from 'lucide-react'
import './CitizenNotifications.css'

const API_URL = 'http://127.0.0.1:8000'

function CitizenNotifications({ token }) {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  async function fetchNotifications() {
    if (!token) return

    try {
      setLoading(true)
      setError('')

      const response = await fetch(
        `${API_URL}/citizen/notifications`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load notifications.')
      }

      setNotifications(data.notifications || [])
      setUnreadCount(data.unread_count || 0)

    } catch (err) {
      setError(err.message || 'Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNotifications()
  }, [token])

  async function markAsRead(notificationId) {
    const notification = notifications.find(
      (item) => item.id === notificationId
    )

    if (!notification || notification.is_read || updatingId !== null) {
      return
    }

    setUpdatingId(notificationId)
    setError('')

    try {
      const response = await fetch(
        `${API_URL}/citizen/notifications/${notificationId}/read`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to mark notification as read.')
      }

      setNotifications((current) =>
        current.map((item) =>
          item.id === notificationId
            ? { ...item, is_read: 1 }
            : item
        )
      )

      setUnreadCount((current) => Math.max(0, current - 1))

    } catch (err) {
      setError(err.message || 'Could not update notification.')
    } finally {
      setUpdatingId(null)
    }
  }

  function formatDate(dateString) {
    if (!dateString) return ''

    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="citizen-notification-wrapper">

      <button
        type="button"
        className="citizen-notification-bell"
        onClick={() => {
          const opening = !isOpen
          setIsOpen(opening)

          if (opening) {
            fetchNotifications()
          }
        }}
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={isOpen}
      >
        <Bell size={20} />

        {unreadCount > 0 && (
          <span className="citizen-notification-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="citizen-notification-panel">

          <div className="citizen-notification-header">
            <div>
              <h3>Notifications</h3>
              <span>{unreadCount} unread</span>
            </div>

            <div className="citizen-notification-header-actions">
              <button
                type="button"
                onClick={fetchNotifications}
                disabled={loading}
                title="Refresh notifications"
              >
                <RefreshCw size={16} />
              </button>

              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close notifications"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {error && (
            <p className="citizen-notification-error">{error}</p>
          )}

          {loading && notifications.length === 0 ? (
            <p className="citizen-notification-empty">
              Loading notifications...
            </p>
          ) : notifications.length === 0 ? (
            <div className="citizen-notification-empty">
              <Bell size={28} />
              <p>No notifications yet.</p>
            </div>
          ) : (
            <div className="citizen-notification-list">

              {notifications.map((notification) => (
                <button
                  type="button"
                  className={`citizen-notification-item ${
                    notification.is_read ? 'read' : 'unread'
                  }`}
                  key={notification.id}
                  onClick={() => markAsRead(notification.id)}
                  disabled={
                    !notification.is_read &&
                    updatingId !== null
                  }
                >
                  <div className="citizen-notification-item-icon">
                    {notification.is_read ? (
                      <CheckCheck size={18} />
                    ) : (
                      <Bell size={18} />
                    )}
                  </div>

                  <div className="citizen-notification-item-content">
                    <strong>{notification.title}</strong>

                    <p>{notification.message}</p>

                    <span>
                      {notification.report_id} · {formatDate(notification.created_at)}
                    </span>

                    {updatingId === notification.id && (
                      <small>Marking as read...</small>
                    )}
                  </div>

                  {!notification.is_read && (
                    <span className="citizen-notification-unread-dot" />
                  )}
                </button>
              ))}

            </div>
          )}

        </div>
      )}

    </div>
  )
}

export default CitizenNotifications
