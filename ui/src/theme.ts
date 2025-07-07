import { createTheme } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'qalia',
  colors: {
    qalia: [
      '#f0f9ff',  // 50
      '#e0f2fe',  // 100
      '#bae6fd',  // 200
      '#7dd3fc',  // 300
      '#38bdf8',  // 400
      '#0ea5e9',  // 500 - primary
      '#0284c7',  // 600
      '#0369a1',  // 700
      '#075985',  // 800
      '#0c4a6e',  // 900
    ],
  },
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif',
  headings: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif',
  },
  defaultRadius: 'md',
  components: {
    Button: {
      defaultProps: {
        radius: 'md',
      },
    },
    Card: {
      defaultProps: {
        radius: 'md',
        shadow: 'sm',
      },
    },
    Modal: {
      defaultProps: {
        centered: true,
        radius: 'md',
      },
    },
  },
}) 