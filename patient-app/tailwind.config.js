import preset from '../frontend-shared/tailwind.preset.js'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [preset],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "../frontend-shared/ui/**/*.{js,ts,jsx,tsx}"
  ],
}
