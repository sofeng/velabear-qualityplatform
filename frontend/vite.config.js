import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'
  const devPort = Number(env.VITE_DEV_PORT || 3000)
  const devHost = env.VITE_DEV_HOST || '0.0.0.0'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '~': resolve(__dirname, 'node_modules'),
      },
    },
    server: {
      port: devPort,
      host: devHost,
      proxy: {
        '^/api/': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '^/media/': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '^/prototype-preview/': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '^/product-preview/': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
      },
      watch: {
        ignored: ['**/dist/**'],
      },
      historyApiFallback: {
        index: '/index.html',
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
    },
    optimizeDeps: {
      include: ['monaco-editor']
    }
  }
})
