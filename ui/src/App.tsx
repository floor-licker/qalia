import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell, Loader, Center } from '@mantine/core'

import { Navbar } from './components/Navbar'
import { Dashboard } from './pages/Dashboard'
import { RecordingSession } from './pages/RecordingSession'
import { TestManager } from './pages/TestManager'
import { GitHubAuth } from './components/GitHubAuth'
import { useAuthStore } from './stores/authStore'

export function App() {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore()

  // Check authentication status when app loads
  useEffect(() => {
    checkAuth()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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