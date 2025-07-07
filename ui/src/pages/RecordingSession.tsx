import { Container, Title, Text } from '@mantine/core'
import { useParams } from 'react-router-dom'

export function RecordingSession() {
  const { repoOwner, repoName } = useParams()

  return (
    <Container size="lg">
      <Title order={1} mb="xl">Recording Session</Title>
      <Text>Recording for repository: {repoOwner}/{repoName}</Text>
      <Text c="dimmed" mt="md">
        This feature will allow you to record user interactions in an embedded browser.
      </Text>
    </Container>
  )
} 