export interface User {
  id: string
  login: string
  name: string
  email: string
  avatar_url: string
}

export interface Session {
  created_at: string
  expires_at: string
  scope: string
}

export interface AuthResponse {
  user: User | null
  authenticated: boolean
  session?: Session
}

export interface Repository {
  id: number
  name: string
  full_name: string
  description: string | null
  private: boolean
  html_url: string
  clone_url: string
  ssh_url: string
  default_branch: string
  language: string | null
  languages_url: string
  stargazers_count: number
  watchers_count: number
  forks_count: number
  size: number
  created_at: string | null
  updated_at: string | null
  pushed_at: string | null
  permissions: {
    admin: boolean
    push: boolean
    pull: boolean
  }
  owner: {
    login: string
    avatar_url: string
    html_url: string
    type: string
  }
}

export interface RecordingSession {
  session_id: string
  repository: string
  user: string
  status: 'created' | 'recording' | 'paused' | 'completed'
  created_at: string
  updated_at: string
}

export interface TestCase {
  id: string
  name: string
  repository: string
  framework: 'playwright' | 'cypress' | 'jest'
  file_path: string
  created_at: string
  updated_at: string
  status: 'draft' | 'active' | 'archived'
} 