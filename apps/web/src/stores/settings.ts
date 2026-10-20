import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
export const useSettings = defineStore('settings', () => {
  const dark = ref(localStorage.getItem('quant-theme') !== 'light');
  watch(dark, value => {
    document.documentElement.classList.toggle('app-dark', value);
    localStorage.setItem('quant-theme', value ? 'dark' : 'light');
  }, { immediate: true });
  return { dark };
});
