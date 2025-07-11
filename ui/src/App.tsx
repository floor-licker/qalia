import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell, Loader, Center } from '@mantine/core'

import { Navbar } from './components/Navbar'
import { Dashboard } from './pages/Dashboard'
import { RecordingSession } from './pages/RecordingSession'
import { TestManager } from './pages/TestManager'
import { GitHubAuth } from './components/GitHubAuth'
import { useAuthStore } from './stores/authStore'

function App() {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore()

  // Check authentication status when app loads (force initial check)
  useEffect(() => {
    console.log('🚀 App mounted - checking authentication...')
    checkAuth(true) // Force initial auth check to bypass circuit breaker
  }, [checkAuth])

  // Also check auth when user might be returning from OAuth
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isAuthenticated) {
        console.log('🔄 Page became visible - checking auth in case user returned from OAuth...')
        checkAuth(true)
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [isAuthenticated, checkAuth])

  if (isLoading) {
    return (
      <Center style={{ height: '100vh' }}>
        <Loader size="lg" />
      </Center>
    )
  }

  if (!isAuthenticated) {
    return <GitHubAuth />
  }

  return (
    <AppShell
      navbar={{ width: 280, breakpoint: 'md' }}
      padding="md"
    >
      <AppShell.Navbar>
        <Navbar />
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/record/:repoOwner/:repoName" element={<RecordingSession />} />
          <Route path="/tests/:repoOwner/:repoName" element={<TestManager />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  )
}

export default App