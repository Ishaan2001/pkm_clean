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

// Push notification event handlers
self.addEventListener('push', (event) => {
  log('Push notification received', event.data?.text());
  
  let notificationData: NotificationOptions = {
    body: 'You have a new reminder',
    icon: '/icon-192.svg',
    badge: '/icon-192.svg',
    data: {
      url: '/',
      timestamp: new Date().toISOString()
    },
    requireInteraction: false,
    silent: false
  };
  
  // Parse notification data if available
  if (event.data) {
    try {
      const pushData = event.data.json();
      notificationData = { ...notificationData, ...pushData };
      log('Parsed push notification data', pushData);
    } catch (error) {
      log('Error parsing push notification data', error);
    }
  }
  
  event.waitUntil(
    self.registration.showNotification('Knowledge Base', {
      ...notificationData,
      tag: 'daily-note-reminder' // Prevents duplicate notifications
    }).then(() => {
      log('Push notification displayed successfully');
    }).catch((error) => {
      log('Error displaying push notification', error);
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  log('Notification clicked', { action: event.action, data: event.notification.data });
  
  event.notification.close();
  
  // Handle notification actions
  if (event.action === 'dismiss') {
    log('Notification dismissed by user');
    return;
  }
  
  // Default action or 'open' action - navigate to the note
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList: readonly WindowClient[]) => {
        // Check if there's already a window/tab open with our app
        for (const client of clientList) {
          if (client.url.includes(self.location.origin)) {
            // Focus the existing window and navigate to the note
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        
        // No existing window found, open a new one
        return self.clients.openWindow(urlToOpen);
      })
      .then(() => {
        log('Navigation completed after notification click');
      })
      .catch((error: any) => {
        log('Error handling notification click', error);
      })
  );
});

self.addEventListener('notificationclose', (event) => {
  log('Notification closed', event.notification.data);
  
  // Track notification close events for analytics if needed
  // You could send this data to your analytics service
});

