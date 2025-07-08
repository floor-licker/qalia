import { Container, Card, Title, Text, Button, Alert, Loader, Group, Stack } from '@mantine/core'
import { IconBrandGithub, IconAlertCircle } from '@tabler/icons-react'
import { useAuthStore } from '../stores/authStore'

export function GitHubAuth() {
  const { 
    isLoading, 
    error, 
    login, 
    clearError 
  } = useAuthStore()

  // Note: App.tsx handles the initial checkAuth, so we don't need to call it here

  const handleLogin = async () => {
    try {
      clearError()
      await login()
    } catch (err) {
      // Error is already handled in the store
      console.error('Login failed:', err)
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

  // Note: This component should only render when NOT authenticated
  // The authenticated state is handled by App.tsx routing

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