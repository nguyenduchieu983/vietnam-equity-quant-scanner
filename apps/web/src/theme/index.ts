import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
export const terminalPreset = definePreset(Aura, {
  semantic: {
    primary: { 50: '{teal.50}', 100: '{teal.100}', 200: '{teal.200}', 300: '{teal.300}', 400: '{teal.400}', 500: '{teal.500}', 600: '{teal.600}', 700: '{teal.700}', 800: '{teal.800}', 900: '{teal.900}', 950: '{teal.950}' },
    colorScheme: {
      dark: { surface: { 0: '#ffffff', 50: '#e9edf4', 100: '#d3dbe7', 200: '#b2bfd1', 300: '#92a4bc', 400: '#71839d', 500: '#52647c', 600: '#35465e', 700: '#243247', 800: '#192436', 900: '#111b2b', 950: '#0b111b' } }
    }
  }
});
