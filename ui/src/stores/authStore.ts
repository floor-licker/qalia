import { create } from 'zustand'
import type { User, AuthResponse } from '../types/auth'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  login: () => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()((set, _get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

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
      set({ isLoading: true, error: null })
      
      // Get OAuth login URL from backend
      const response = await fetch('/api/auth/login')
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to initiate login')
      }
      
      // Redirect to GitHub OAuth
      window.location.href = data.auth_url
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed'
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

  checkAuth: async () => {
    try {
      set({ isLoading: true, error: null })
      
      // Check current authentication status
      const response = await fetch('/api/auth/user', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error('Failed to check authentication')
      }
      
      const data: AuthResponse = await response.json()
      
      set({
        user: data.user,
        isAuthenticated: data.authenticated,
        isLoading: false,
        error: null
      })
      
    } catch (error) {
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