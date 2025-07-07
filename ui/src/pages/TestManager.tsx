import { Container, Title, Text } from '@mantine/core'
import { useParams } from 'react-router-dom'

export function TestManager() {
  const { repoOwner, repoName } = useParams()

  return (
    <Container size="lg">
      <Title order={1} mb="xl">Test Manager</Title>
      <Text>Managing tests for repository: {repoOwner}/{repoName}</Text>
      <Text c="dimmed" mt="md">
        This feature will show and manage generated test cases.
      </Text>
    </Container>
  )
} 