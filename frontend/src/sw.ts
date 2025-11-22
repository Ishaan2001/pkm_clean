/// <reference lib="webworker" />
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { clientsClaim } from 'workbox-core'
import { NavigationRoute, registerRoute } from 'workbox-routing'

declare const self: ServiceWorkerGlobalScope

// Enhanced logging for service worker
const log = (message: string, data?: any) => {
  console.log(`[ServiceWorker] ${message}`, data || '');
};

// self.__WB_MANIFEST is default injection point
precacheAndRoute(self.__WB_MANIFEST)
log('Service worker precaching configured');

// clean old assets
cleanupOutdatedCaches()

let allowlist: undefined | RegExp[]
if (import.meta.env.DEV)
  allowlist = [/^\/$/]

// to allow work offline
registerRoute(new NavigationRoute(
  createHandlerBoundToURL('/index.html'),
  { allowlist }
))

self.skipWaiting()
clientsClaim()

// Service worker lifecycle logging
self.addEventListener('install', (_event) => {
  log('Service worker installing', { timestamp: new Date().toISOString() });
});

self.addEventListener('activate', (_event) => {
  log('Service worker activated', { timestamp: new Date().toISOString() });
});

self.addEventListener('message', (event) => {
  log('Service worker message received', event.data);
  
  // Handle debugging requests
  if (event.data && event.data.type === 'GET_SW_STATE') {
    event.ports[0].postMessage({
      swVersion: '1.0.0',
      timestamp: new Date().toISOString(),
      ready: true
    });
  }
});

