const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'https://httpbin.org/html',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    supportFile: false,
    video: true,
    screenshotOnRunFailure: true,
  },
})
