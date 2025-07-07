import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'

import App from './App.tsx'
import { theme } from './theme'

// Import Mantine styles
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

// Import Tailwind CSS
import './index.css'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme}>
        <Notifications />
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  </React.StrictMode>,
) 