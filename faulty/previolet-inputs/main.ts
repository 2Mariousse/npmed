import Vue from 'vue'
import App from './App.vue'
import VueClipboard from 'vue-clipboard2'
const PrevioletSDK = require('previolet').default

import './styles/index.scss'

Vue.use(VueClipboard)
Vue.config.productionTip = false

const sdk = new PrevioletSDK({
  instance: 'c16521384',
  tokenFallback: 'tk-yKDxOebZtXQ2Ghqh3xTXelSIx5qKNL',
  region: 'eu.east1',
  debug: true,
})

// Add the SDK as global
// @ts-ignore
window.backendZero = sdk

new Vue({
  render: (h) => h(App)
}).$mount('#app')
