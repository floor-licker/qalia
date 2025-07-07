import { Container, Title, Text, Button, Group, Card, SimpleGrid } from '@mantine/core'
import { IconPlus, IconGitBranch, IconTestPipe } from '@tabler/icons-react'

export function Dashboard() {
  return (
    <Container size="lg">
      <Title order={1} mb="xl">Qalia Dashboard</Title>
      
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Card.Section withBorder inheritPadding py="xs">
            <Group justify="space-between">
              <Text fw={500}>Recording Sessions</Text>
              <IconTestPipe size={20} />
            </Group>
          </Card.Section>

          <Text size="sm" c="dimmed" mt="sm">
            Create and manage test recording sessions for your repositories.
          </Text>

          <Button fullWidth mt="md" radius="md">
            <IconPlus size={16} style={{ marginRight: 8 }} />
            New Recording Session
          </Button>
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Card.Section withBorder inheritPadding py="xs">
            <Group justify="space-between">
              <Text fw={500}>Test Management</Text>
              <IconGitBranch size={20} />
            </Group>
          </Card.Section>

          <Text size="sm" c="dimmed" mt="sm">
            View and manage generated test cases across your repositories.
          </Text>

          <Button fullWidth mt="md" radius="md" variant="light">
            View Test Cases
          </Button>
        </Card>
      </SimpleGrid>

      <Card shadow="sm" padding="lg" radius="md" withBorder mt="xl">
        <Title order={3} mb="md">Getting Started</Title>
        <Text size="sm" c="dimmed">
          Welcome to Qalia! This UI allows you to record user interactions and automatically 
          generate test cases. Start by connecting your GitHub account and selecting a repository 
          to begin recording.
        </Text>
      </Card>
    </Container>
  )
} 