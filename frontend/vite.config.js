import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"


// Minimal Web Crypto polyfill for Node.js environments that don't expose
// `globalThis.crypto.getRandomValues` (older Node versions, e.g. v16).
// Vite (and some dependencies) expect the Web Crypto API. This polyfill
// first tries to use `crypto.webcrypto` if available, otherwise provides
// a small `getRandomValues` shim backed by Node's `crypto.randomBytes`.
import nodeCrypto from 'crypto'
if (typeof globalThis.crypto === 'undefined' || typeof globalThis.crypto.getRandomValues !== 'function') {
  if (nodeCrypto.webcrypto && typeof nodeCrypto.webcrypto.getRandomValues === 'function') {
    globalThis.crypto = nodeCrypto.webcrypto
  } else {
    // Fallback implementation that fills a typed array using randomBytes.
    globalThis.crypto = {
      getRandomValues: (arr) => {
        if (!(arr instanceof Uint8Array)) {
          throw new TypeError('Expected Uint8Array')
        }
        const buf = nodeCrypto.randomBytes(arr.length)
        arr.set(buf)
        return arr
      }
    }
  }
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // 'react-native': 'react-native-web',
    },
  },
})
