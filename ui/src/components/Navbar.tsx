import { Stack, Group, Text, Button, Avatar, Divider, UnstyledButton } from '@mantine/core'
import { IconHome, IconTestPipe, IconRecordMail, IconSettings, IconBrandGithub, IconLogout } from '@tabler/icons-react'
import { useAuthStore } from '@/stores/authStore'
import { Link, useLocation } from 'react-router-dom'

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  const handleLogout = async () => {
    try {
      await logout()
    } catch (err) {
      console.error('Logout failed:', err)
    }
  }

  return (
    <Stack h="100%" p="md" justify="space-between">
      {/* Header */}
      <div>
        <Group justify="center" mb="md">
          <Text fw={700} size="lg" c="qalia.6">
            Qalia
          </Text>
        </Group>

        <Divider mb="md" />

        {/* Navigation Links */}
        {isAuthenticated ? (
          <Stack gap="xs">
            <NavLink
              to="/"
              icon={<IconHome size={16} />}
              label="Dashboard"
              active={isActive('/')}
            />
            <NavLink
              to="/record"
              icon={<IconRecordMail size={16} />}
              label="Record Tests"
              active={isActive('/record')}
            />
            <NavLink
              to="/tests"
              icon={<IconTestPipe size={16} />}
              label="Test Manager"
              active={isActive('/tests')}
            />
            <NavLink
              to="/settings"
              icon={<IconSettings size={16} />}
              label="Settings"
              active={isActive('/settings')}
            />
          </Stack>
        ) : (
          <Stack gap="xs">
            <Text c="dimmed" size="sm" ta="center">
              Sign in to access features
            </Text>
          </Stack>
        )}
      </div>

      {/* User Info / Auth */}
      <div>
        <Divider mb="md" />
        
        {isAuthenticated && user ? (
          <Stack gap="xs">
            <Group gap="xs">
              <Avatar src={user.avatar_url} size="sm" radius="md" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text size="sm" fw={500} truncate>
                  {user.name || user.login}
                </Text>
                <Text size="xs" c="dimmed" truncate>
                  @{user.login}
                </Text>
              </div>
            </Group>
            
            <Button
              variant="light"
              size="xs"
              leftSection={<IconLogout size={14} />}
              onClick={handleLogout}
              fullWidth
            >
              Sign Out
            </Button>
          </Stack>
        ) : (
          <Button
            component={Link}
            to="/auth"
            variant="light"
            leftSection={<IconBrandGithub size={16} />}
            fullWidth
          >
            Sign In
          </Button>
        )}
      </div>
    </Stack>
  )
}

interface NavLinkProps {
  to: string
  icon: React.ReactNode
  label: string
  active?: boolean
}

function NavLink({ to, icon, label, active }: NavLinkProps) {
  return (
    <UnstyledButton
      component={Link}
      to={to}
      style={(theme) => ({
        display: 'block',
        width: '100%',
        padding: theme.spacing.xs,
        borderRadius: theme.radius.sm,
        color: active ? theme.colors.qalia[6] : theme.colors.gray[7],
        backgroundColor: active ? theme.colors.qalia[0] : 'transparent',
        '&:hover': {
          backgroundColor: active ? theme.colors.qalia[1] : theme.colors.gray[0],
        },
      })}
    >
      <Group gap="xs">
        {icon}
        <Text size="sm" fw={active ? 500 : 400}>
          {label}
        </Text>
      </Group>
    </UnstyledButton>
  )
} 