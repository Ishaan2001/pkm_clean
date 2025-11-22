import { api } from './api';

// Get VAPID public key from environment
const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY;

interface PushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

interface PushSubscriptionData {
  endpoint: string;
  keys: PushSubscriptionKeys;
  user_agent?: string;
}

interface SubscriptionResponse {
  message: string;
  subscription_id?: number;
}

class NotificationService {
  /**
   * Convert VAPID public key from base64url to Uint8Array
   */
  private static urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  }

  /**
   * Check if push notifications are supported in this browser
   */
  static isPushNotificationSupported(): boolean {
    return (
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  /**
   * Get service worker registration with timeout to prevent hanging
   */
  private static async getServiceWorkerWithTimeout(timeoutMs = 10000): Promise<ServiceWorkerRegistration> {
    return new Promise(async (resolve, reject) => {
      const timeout = setTimeout(() => {
        console.error('❌ Service worker registration timeout after', timeoutMs, 'ms');
        reject(new Error('Service worker registration timeout. Please refresh the page and try again.'));
      }, timeoutMs);

      try {
        console.log('⏰ Waiting for service worker registration...');
        
        // First check if service worker is already registered
        const currentRegistration = await navigator.serviceWorker.getRegistration();
        console.log('🔍 Current registration:', currentRegistration);
        
        if (currentRegistration) {
          console.log('📋 Registration details:', {
            scope: currentRegistration.scope,
            active: !!currentRegistration.active,
            waiting: !!currentRegistration.waiting,
            installing: !!currentRegistration.installing
          });
          
          if (currentRegistration.active) {
            console.log('✅ Found existing active service worker');
            clearTimeout(timeout);
            resolve(currentRegistration);
            return;
          }
        }

        // If no active service worker, wait a bit for it to become ready
        console.log('⏳ Waiting for service worker to become ready...');
        const registration = await navigator.serviceWorker.ready;
        console.log('✅ Service worker became ready:', {
          scope: registration.scope,
          active: !!registration.active
        });
        clearTimeout(timeout);
        resolve(registration);
      } catch (error) {
        clearTimeout(timeout);
        console.error('❌ Service worker registration failed:', error);
        reject(new Error('Failed to register service worker. Please refresh the page and try again.'));
      }
    });
  }

  /**
   * Check if notifications are currently enabled
   */
  static areNotificationsEnabled(): boolean {
    return Notification.permission === 'granted';
  }

  /**
   * Check current notification permission status
   */
  static getNotificationPermission(): NotificationPermission {
    return Notification.permission;
  }

  /**
   * Request notification permission from the user
   * Must be called from a user gesture (click event)
   */
  static async requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      throw new Error('This browser does not support notifications');
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission === 'denied') {
      throw new Error('Notifications are blocked. Please enable them in your browser settings.');
    }

    // Request permission
    const permission = await Notification.requestPermission();
    return permission;
  }

  /**
   * Get the current push subscription from the service worker
   */
  static async getCurrentSubscription(): Promise<PushSubscription | null> {
    if (!('serviceWorker' in navigator)) {
      return null;
    }

    const registration = await navigator.serviceWorker.ready;
    return registration.pushManager.getSubscription();
  }

  /**
   * Subscribe to push notifications
   * Must be called from a user gesture and after permission is granted
   */
  static async subscribeToNotifications(): Promise<SubscriptionResponse> {
    try {
      console.log('🔔 Starting notification subscription process...');
      
      // Validate environment
      if (!VAPID_PUBLIC_KEY) {
        console.error('❌ VAPID public key not configured');
        throw new Error('VAPID public key not configured');
      }
      console.log('✅ VAPID public key loaded:', VAPID_PUBLIC_KEY.substring(0, 20) + '...');

      if (!this.isPushNotificationSupported()) {
        console.error('❌ Push notifications not supported');
        throw new Error('Push notifications are not supported in this browser');
      }
      console.log('✅ Push notifications supported');

      // Check permission
      console.log('🔐 Requesting notification permission...');
      const permission = await this.requestNotificationPermission();
      console.log('🔐 Permission result:', permission);
      
      if (permission !== 'granted') {
        console.error('❌ Permission denied:', permission);
        throw new Error('Notification permission denied');
      }

      // Get service worker registration with timeout
      console.log('⚙️ Getting service worker registration...');
      const registration = await this.getServiceWorkerWithTimeout();
      console.log('✅ Service worker ready');

      // Check for existing subscription
      console.log('🔍 Checking for existing subscription...');
      const existingSubscription = await registration.pushManager.getSubscription();
      
      if (existingSubscription) {
        console.log('♻️ Found existing subscription, updating backend...');
        // Send existing subscription to backend
        return this.sendSubscriptionToBackend(existingSubscription);
      }

      // Create new subscription
      console.log('🆕 Creating new push subscription...');
      const applicationServerKey = this.urlBase64ToUint8Array(VAPID_PUBLIC_KEY);
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey.buffer
      });
      console.log('✅ Push subscription created successfully');

      return this.sendSubscriptionToBackend(subscription);
      
    } catch (error) {
      console.error('💥 Error in subscribeToNotifications:', error);
      throw error;
    }
  }

  /**
   * Send subscription data to the backend
   */
  private static async sendSubscriptionToBackend(subscription: PushSubscription): Promise<SubscriptionResponse> {
    try {
      console.log('📤 Sending subscription to backend...');
      
      // Check if user is authenticated before proceeding
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('❌ No authentication token found');
        throw new Error('You must be logged in to enable notifications');
      }
      
      const subscriptionJson = subscription.toJSON();
      console.log('📋 Subscription JSON:', subscriptionJson);
      
      if (!subscriptionJson.keys) {
        console.error('❌ Invalid subscription keys');
        throw new Error('Invalid subscription keys');
      }

      const subscriptionData: PushSubscriptionData = {
        endpoint: subscription.endpoint,
        keys: {
          p256dh: subscriptionJson.keys.p256dh!,
          auth: subscriptionJson.keys.auth!
        },
        user_agent: navigator.userAgent
      };

      console.log('📦 Subscription data prepared:', {
        endpoint: subscriptionData.endpoint.substring(0, 50) + '...',
        keys: { p256dh: '***', auth: '***' },
        user_agent: subscriptionData.user_agent
      });

      console.log('🚀 Making API call to /api/push/subscribe...');
      const response = await api.post<SubscriptionResponse>('/api/push/subscribe', subscriptionData, true, true);
      console.log('✅ Subscription sent to backend successfully:', response);
      return response;
    } catch (error) {
      console.error('💥 Failed to send subscription to backend:', error);
      
      // Handle authentication errors specifically
      if (error instanceof Error) {
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
          throw new Error('Authentication failed. Please refresh the page and try again.');
        }
        if (error.message.includes('403') || error.message.includes('Forbidden')) {
          throw new Error('Not authorized to enable notifications.');
        }
        if (error.message.includes('Network error')) {
          throw new Error('Network error. Please check your connection and try again.');
        }
        throw new Error(`Failed to enable push notifications: ${error.message}`);
      }
      throw new Error('Failed to enable push notifications on server');
    }
  }

  /**
   * Unsubscribe from push notifications
   */
  static async unsubscribeFromNotifications(): Promise<boolean> {
    if (!('serviceWorker' in navigator)) {
      return false;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (!subscription) {
        console.log('No active subscription found');
        return true;
      }

      // Unsubscribe from the push service
      const unsubscribed = await subscription.unsubscribe();

      if (unsubscribed) {
        // Notify backend to remove subscription
        try {
          await api.delete(`/api/push/unsubscribe?endpoint=${encodeURIComponent(subscription.endpoint)}`, true, true);
          console.log('Successfully unsubscribed from push notifications');
        } catch (error) {
          console.error('Failed to notify backend about unsubscription:', error);
          // Continue anyway since local unsubscription was successful
        }
      }

      return unsubscribed;
    } catch (error) {
      console.error('Failed to unsubscribe from notifications:', error);
      return false;
    }
  }

  /**
   * Get user's subscription status and devices
   */
  static async getSubscriptionStatus(): Promise<any> {
    try {
      return await api.get('/api/push/subscriptions', true, true);
    } catch (error) {
      console.error('Failed to get subscription status:', error);
      throw error;
    }
  }

  /**
   * Send a test notification (for debugging)
   */
  static async sendTestNotification(): Promise<void> {
    try {
      await api.post('/api/push/test-notification', undefined, true, true);
      console.log('Test notification triggered');
    } catch (error) {
      console.error('Failed to send test notification:', error);
      throw error;
    }
  }

  /**
   * Check if the current device is subscribed
   */
  static async isCurrentDeviceSubscribed(): Promise<boolean> {
    try {
      const currentSubscription = await this.getCurrentSubscription();
      if (!currentSubscription) {
        return false;
      }

      // Check with backend if this subscription is still valid
      const status = await this.getSubscriptionStatus();
      const currentEndpoint = currentSubscription.endpoint;
      
      return status.subscriptions.some((sub: any) => 
        sub.endpoint.startsWith(currentEndpoint.substring(0, 50))
      );
    } catch (error) {
      console.error('Failed to check subscription status:', error);
      return false;
    }
  }

  /**
   * Get notification preferences summary for UI
   */
  static async getNotificationSummary(): Promise<{
    supported: boolean;
    permission: NotificationPermission;
    subscribed: boolean;
    deviceCount: number;
  }> {
    const supported = this.isPushNotificationSupported();
    const permission = this.getNotificationPermission();
    
    let subscribed = false;
    let deviceCount = 0;

    if (supported && permission === 'granted') {
      try {
        subscribed = await this.isCurrentDeviceSubscribed();
        const status = await this.getSubscriptionStatus();
        deviceCount = status.total_count;
      } catch (error) {
        console.error('Failed to get notification summary:', error);
      }
    }

    return {
      supported,
      permission,
      subscribed,
      deviceCount
    };
  }
}

export default NotificationService;