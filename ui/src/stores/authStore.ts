import { create } from 'zustand'
import type { User, AuthResponse } from '../types/auth'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  lastAuthCheck: number | null
  
  // Actions
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  login: () => Promise<void>
  logout: () => Promise<void>
  checkAuth: (force?: boolean) => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  lastAuthCheck: null,

  setUser: (user) => {
    set({ 
      user, 
      isAuthenticated: !!user,
      error: null 
    })
  },

  setLoading: (loading) => {
    set({ isLoading: loading })
  },

  setError: (error) => {
    set({ error })
  },

  clearError: () => {
    set({ error: null })
  },

  login: async () => {
    try {
      console.log('🔐 Starting OAuth login process...')
      set({ isLoading: true, error: null })
      
      // Get OAuth login URL from backend
      console.log('🔄 Fetching OAuth login URL from backend...')
      const response = await fetch('/api/auth/login')
      const data = await response.json()
      
      console.log('📝 Login response:', { status: response.status, ok: response.ok, data })
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to initiate login')
      }
      
      // Redirect to GitHub OAuth
      console.log('🔗 Redirecting to GitHub OAuth:', data.auth_url)
      window.location.href = data.auth_url
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed'
      console.error('❌ Login failed:', error)
      set({ 
        error: errorMessage,
        isLoading: false 
      })
      throw error
    }
  },

  logout: async () => {
    try {
      set({ isLoading: true, error: null })
      
      // Call logout endpoint
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error('Logout failed')
      }
      
      // Clear user state
      set({ 
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      })
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed'
      set({ 
        error: errorMessage,
        isLoading: false 
      })
      throw error
    }
  },

  checkAuth: async (force = false) => {
    const state = get()
    const now = Date.now()
    
    // Circuit breaker: prevent requests within 5 seconds of last check (unless forced)
    if (!force && state.lastAuthCheck && (now - state.lastAuthCheck) < 5000) {
      console.log('🔄 Skipping auth check - too recent (circuit breaker)')
      return
    }
    
    // Prevent multiple concurrent requests
    if (state.isLoading) {
      console.log('🔄 Skipping auth check - already in progress')
      return
    }
    
    try {
      console.log('🔍 Checking authentication status...')
      console.log('🔍 Force check:', force)
      console.log('🔍 Current auth state:', { 
        isAuthenticated: state.isAuthenticated, 
        user: state.user?.login || 'none',
        lastCheck: state.lastAuthCheck ? new Date(state.lastAuthCheck).toISOString() : 'never'
      })
      console.log('🍪 Current cookies:', document.cookie)
      console.log('🍪 Cookie breakdown:', document.cookie.split(';').map(c => c.trim()))
      
      // Check for qalia_session cookie specifically
      const qaliaCookie = document.cookie.split(';').find(c => c.trim().startsWith('qalia_session='))
      if (qaliaCookie) {
        console.log('🍪 Found qalia_session cookie:', qaliaCookie.split('=')[1]?.substring(0, 8) + '...')
      } else {
        console.log('🍪 No qalia_session cookie found')
      }
      
      set({ isLoading: true, error: null, lastAuthCheck: now })
      
      // Check current authentication status
      console.log('🔍 Making auth check request to /api/auth/user...')
      const response = await fetch('/api/auth/user', {
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      })
      
      console.log('📝 Auth check response:', { 
        status: response.status, 
        ok: response.ok,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      })
      
      if (!response.ok) {
        console.error('❌ Auth check request failed:', response.status, response.statusText)
        throw new Error(`Failed to check authentication: ${response.status} ${response.statusText}`)
      }
      
      const data: AuthResponse = await response.json()
      console.log('📝 Auth check data:', data)
      console.log('📝 Auth check summary:', { 
        authenticated: data.authenticated, 
        user: data.user?.login || 'none',
        hasUserData: !!data.user
      })
      
      set({
        user: data.user,
        isAuthenticated: data.authenticated,
        isLoading: false,
        error: null
      })
      
      if (data.authenticated) {
        console.log('✅ User is authenticated:', data.user?.login)
        console.log('✅ Authentication successful - user should be logged in')
      } else {
        console.log('❌ User is not authenticated')
        console.log('❌ Will show login page')
      }
      
    } catch (error) {
      console.error('❌ Auth check failed:', error)
      console.error('❌ Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : 'No stack trace'
      })
      // If auth check fails, user is likely not authenticated
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null // Don't show error for failed auth check
      })
    }
  }
})) 