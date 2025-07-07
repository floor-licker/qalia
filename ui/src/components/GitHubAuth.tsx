import { useEffect } from 'react'
import { Container, Card, Title, Text, Button, Alert, Loader, Group, Avatar, Stack } from '@mantine/core'
import { IconBrandGithub, IconLogout, IconAlertCircle } from '@tabler/icons-react'
import { useAuthStore } from '@/stores/authStore'

export function GitHubAuth() {
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    error, 
    login, 
    logout, 
    checkAuth, 
    clearError 
  } = useAuthStore()

  // Check authentication status on component mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const handleLogin = async () => {
    try {
      clearError()
      await login()
    } catch (err) {
      // Error is already handled in the store
      console.error('Login failed:', err)
    }
  }

  const handleLogout = async () => {
    try {
      clearError()
      await logout()
    } catch (err) {
      // Error is already handled in the store
      console.error('Logout failed:', err)
    }
  }

  if (isLoading) {
    return (
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Group justify="center">
            <Loader size="lg" />
            <Text>Checking authentication...</Text>
          </Group>
        </Card>
      </Container>
    )
  }

  if (isAuthenticated && user) {
    return (
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack align="center" gap="md">
            <Avatar src={user.avatar_url} size="xl" radius="md" />
            
            <div style={{ textAlign: 'center' }}>
              <Title order={2}>{user.name || user.login}</Title>
              <Text c="dimmed">@{user.login}</Text>
              {user.email && <Text size="sm" c="dimmed">{user.email}</Text>}
            </div>

            <Alert 
              icon={<IconBrandGithub size={16} />} 
              color="green" 
              variant="light"
              style={{ width: '100%' }}
            >
              Successfully authenticated with GitHub
            </Alert>

            <Button 
              leftSection={<IconLogout size={16} />}
              variant="light" 
              color="red"
              onClick={handleLogout}
              loading={isLoading}
            >
              Sign Out
            </Button>
          </Stack>
        </Card>
      </Container>
    )
  }

  return (
    <Container size="sm" py="xl">
      <Card shadow="sm" padding="xl" radius="md" withBorder>
        <Stack align="center" gap="md">
          <IconBrandGithub size={64} color="var(--mantine-color-gray-6)" />
          
          <div style={{ textAlign: 'center' }}>
            <Title order={2}>Sign in to Qalia</Title>
            <Text c="dimmed" mt="sm">
              Connect your GitHub account to access the embedded UI recorder
            </Text>
          </div>

          {error && (
            <Alert 
              icon={<IconAlertCircle size={16} />} 
              color="red" 
              variant="light"
              style={{ width: '100%' }}
            >
              {error}
            </Alert>
          )}

          <Button 
            leftSection={<IconBrandGithub size={16} />}
            size="lg"
            onClick={handleLogin}
            loading={isLoading}
          >
            Sign in with GitHub
          </Button>

          <Text size="xs" c="dimmed" style={{ textAlign: 'center' }}>
            Qalia will access your GitHub repositories to help you<br />
            create and manage automated test cases.
          </Text>
        </Stack>
      </Card>
    </Container>
  )
} 