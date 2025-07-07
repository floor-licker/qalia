import { Routes, Route } from 'react-router-dom'
import { AppShell } from '@mantine/core'

import { Navbar } from '@/components/Navbar'
import { Dashboard } from '@/pages/Dashboard'
import { RecordingSession } from '@/pages/RecordingSession'
import { TestManager } from '@/pages/TestManager'
import { GitHubAuth } from '@/components/GitHubAuth'

function App() {
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
          <Route path="/auth" element={<GitHubAuth />} />
          <Route path="/record/:repoOwner/:repoName" element={<RecordingSession />} />
          <Route path="/tests/:repoOwner/:repoName" element={<TestManager />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  )
}

export default App 