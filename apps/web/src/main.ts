import { createApp } from 'vue';
import { createPinia } from 'pinia';
import PrimeVue from 'primevue/config';
import ToastService from 'primevue/toastservice';
import Tooltip from 'primevue/tooltip';
import App from './App.vue';
import { router } from './router';
import { terminalPreset } from './theme';
import 'primeicons/primeicons.css';
import './theme/terminal.css';

createApp(App).use(createPinia()).use(router)
  .use(PrimeVue, { theme: { preset: terminalPreset, options: { darkModeSelector: '.app-dark' } } })
  .use(ToastService).directive('tooltip', Tooltip).mount('#app');
