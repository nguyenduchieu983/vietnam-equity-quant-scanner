import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
  plugins: [vue()],
  // Prebundle lazy-route controls before login: a late optimizer reload would
  // correctly clear the memory-only token but unexpectedly interrupt navigation.
  optimizeDeps: { include: ['primevue/panel','primevue/inputnumber','primevue/progressbar','primevue/drawer','primevue/select','primevue/datatable','primevue/column','lightweight-charts'] },
  server: { proxy: { '/api': 'http://127.0.0.1:3000' } },
  build: { chunkSizeWarningLimit: 700 }
});
