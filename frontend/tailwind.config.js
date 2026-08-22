/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Razorpay brand palette
        rzp: {
          blue:    '#2D65F8',
          'blue-light': '#EEF3FF',
          'blue-mid':   '#D0DFFE',
        },
        // Semantic states (muted, professional)
        matched:     '#059669',
        'matched-bg':'#ECFDF5',
        pending:     '#D97706',
        'pending-bg':'#FFFBEB',
        disc:        '#DC2626',
        'disc-bg':   '#FEF2F2',
        // Neutral surface system
        surface:  '#FFFFFF',
        canvas:   '#F4F6FA',
        border:   '#E5E7EB',
        'border-strong': '#D1D5DB',
        muted:    '#6B7280',
        subtle:   '#9CA3AF',
        ink:      '#111827',
        'ink-2':  '#374151',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        card:  '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
        panel: '0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.06)',
        drawer:'0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)',
      }
    },
  },
  plugins: [],
}
