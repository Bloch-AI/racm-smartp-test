/**
 * SmartPapers Tailwind CSS Configuration
 * Shared configuration for all pages using Tailwind CDN
 */
tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                'sans': ['Inter', 'system-ui', 'sans-serif'],
                'display': ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
                'mono': ['DM Mono', 'monospace'],
            },
            colors: {
                // Bloch AI brand blue
                primary: {
                    50: '#e6f4fa',
                    100: '#cce9f5',
                    200: '#99d3eb',
                    300: '#66bde1',
                    400: '#33a7d7',
                    500: '#008bd1',
                    600: '#007ab8',
                    700: '#00689e',
                    800: '#005785',
                    900: '#00456b',
                },
                success: { light: '#dcfce7', DEFAULT: '#22c55e', dark: '#15803d' },
                warning: { light: '#fef3c7', DEFAULT: '#f59e0b', dark: '#b45309' },
                danger: { light: '#fee2e2', DEFAULT: '#ef4444', dark: '#b91c1c' },
                info: { light: '#dbeafe', DEFAULT: '#3b82f6', dark: '#1d4ed8' },
                felix: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                }
            }
        }
    }
};
