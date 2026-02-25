import { createApp } from 'vue'
import { createPinia } from 'pinia'

import vuetify from './plugins/vuetify'
import { createGtag } from 'vue-gtag'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(createGtag({
  tagId: import.meta.env.VITE_GOOGLE_ANALYTICS_ID,
  pageTracker: { router }
}))

app.mount('#app')