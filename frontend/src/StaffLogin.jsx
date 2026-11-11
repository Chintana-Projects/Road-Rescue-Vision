
import { useState } from 'react'
import {
  LockKeyhole,
  ShieldCheck,
  LoaderCircle,
  AlertCircle,
  UserRound,
  Users,
  ArrowLeft,
  UserPlus,
  Eye,
  EyeOff,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

function StaffLogin({ onLogin, onCitizenLogin }) {
  const [showPassword, setShowPassword] = useState(false)
  const [role, setRole] = useState('')
  const [mode, setMode] = useState('login')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function resetForm() {
    setUsername('')
    setPassword('')
    setFullName('')
    setEmail('')
    setError('')
    setShowPassword(false)
    setMode('login')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      let endpoint
      let body

      if (role === 'staff') {
        endpoint = '/staff/login'
        body = { username, password }
      } else if (mode === 'register') {
        endpoint = '/citizen/register'
        body = {
          full_name: fullName,
          email,
          username,
          password,
        }
      } else {
        endpoint = '/citizen/login'
        body = {
          login: username,
          password,
        }
      }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed.')
      }

      if (role === 'staff') {
        onLogin(data.access_token, data.username || username)
      } else {
        onCitizenLogin(
          data.access_token,
          data.username,
          data.full_name
        )
      }
    } catch (err) {
      setError(err.message || 'Unable to connect to the server.')
    } finally {
      setLoading(false)
    }
  }

  function selectRole(selectedRole) {
    setRole(selectedRole)
    resetForm()
  }

  return (
    <div className="staff-login-page">
      <div className="staff-login-card">

        <div className="staff-login-icon">
          <ShieldCheck size={30} />
        </div>

        <span className="staff-login-kicker">
          ROADRESCUE VISION
        </span>

        {!role ? (
          <>
            <h1>
              Welcome <span>Back</span>
            </h1>

            <p>Select your role to continue.</p>

            <button
              type="button"
              className="citizen-access-button"
              onClick={() => selectRole('citizen')}
            >
              <Users size={18} />
              CITIZEN
            </button>

            <button
              type="button"
              className="staff-access-button"
              onClick={() => selectRole('staff')}
            >
              <ShieldCheck size={18} />
              STAFF
            </button>

            <div className="staff-login-footer">
              Road damage reporting and inspection portal
            </div>
          </>
        ) : (
          <>
            <button
              type="button"
              className="citizen-access-button"
              onClick={() => {
                setRole('')
                resetForm()
              }}
            >
              <ArrowLeft size={16} />
              BACK TO ROLE SELECTION
            </button>

            <h1>
              {role === 'staff' ? (
                <>Staff <span>Login</span></>
              ) : mode === 'register' ? (
                <>Citizen <span>Registration</span></>
              ) : (
                <>Citizen <span>Login</span></>
              )}
            </h1>

            <p>
              {role === 'staff'
                ? 'Sign in to access the road inspection administration dashboard.'
                : mode === 'register'
                  ? 'Create your account to submit and track road damage reports.'
                  : 'Sign in to continue to citizen road reporting.'}
            </p>

            <form onSubmit={handleSubmit}>

              {role === 'citizen' && mode === 'register' && (
                <>
                  <label htmlFor="citizen-full-name">
                    FULL NAME
                  </label>

                  <input
                    id="citizen-full-name"
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Enter your full name"
                    autoComplete="name"
                    required
                  />

                  <label htmlFor="citizen-email">
                    EMAIL
                  </label>

                  <input
                    id="citizen-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="Enter your email"
                    autoComplete="email"
                    required
                  />
                </>
              )}

              <label htmlFor="login-username">
  {role === 'citizen' && mode === 'login'
    ? 'USERNAME OR EMAIL'
    : 'USERNAME'}
</label>

              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder={
  role === 'citizen'
    ? mode === 'register'
      ? 'Create a username (e.g. chintana123)'
      : 'Enter username or email'
    : 'Enter staff username'
}
                autoComplete="username"
                required
              />

              <label htmlFor="login-password">
                PASSWORD
              </label>

              <div className="staff-password-field">
                <LockKeyhole size={17} />

                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter password"
                  autoComplete={
                    mode === 'register'
                      ? 'new-password'
                      : 'current-password'
                  }
                  minLength={
                    role === 'citizen' && mode === 'register'
                      ? 8
                      : undefined
                  }
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>

              {error && (
                <div className="staff-login-error" role="alert">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="login-submit-button"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <LoaderCircle className="spin" size={17} />
                    PLEASE WAIT...
                  </>
                ) : role === 'staff' ? (
                  'SIGN IN SECURELY'
                ) : mode === 'register' ? (
                  <>
                    <UserPlus size={17} />
                    CREATE ACCOUNT
                  </>
                ) : (
                  'SIGN IN'
                )}
              </button>
            </form>

            {role === 'citizen' && (
              <button
                type="button"
                className="citizen-access-button"
                onClick={() => {
                  setMode(mode === 'login' ? 'register' : 'login')
                  setUsername('')
                  setPassword('')
                  setFullName('')
                  setEmail('')
                  setError('')
                  setShowPassword(false)
                }}
              >
                {mode === 'login'
                  ? 'NEW CITIZEN? CREATE ACCOUNT'
                  : 'ALREADY HAVE AN ACCOUNT? LOGIN'}
              </button>
            )}

            <div className="staff-login-footer">
              {role === 'staff' ? (
                <>
                  <ShieldCheck size={14} />
                  Authorized staff access only
                </>
              ) : (
                <>
                  <UserRound size={14} />
                  Citizen reporting portal
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default StaffLogin
