import React, { useState, useEffect } from 'react';
import NotificationService from '../services/notifications';

interface NotificationSummary {
  supported: boolean;
  permission: NotificationPermission;
  subscribed: boolean;
  deviceCount: number;
}

interface NotificationSettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [testing, setTesting] = useState(false);
  const [summary, setSummary] = useState<NotificationSummary>({
    supported: false,
    permission: 'default',
    subscribed: false,
    deviceCount: 0
  });
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchNotificationSummary = async () => {
    try {
      setError(null);
      const data = await NotificationService.getNotificationSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to fetch notification summary:', err);
      setError('Failed to load notification settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchNotificationSummary();
    }
  }, [isOpen]);

  const handleEnableNotifications = async () => {
    setEnabling(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await NotificationService.subscribeToNotifications();
      setSuccessMessage(response.message);
      await fetchNotificationSummary();
    } catch (err: any) {
      console.error('Failed to enable notifications:', err);
      setError(err.message || 'Failed to enable notifications');
    } finally {
      setEnabling(false);
    }
  };

  const handleDisableNotifications = async () => {
    setDisabling(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const success = await NotificationService.unsubscribeFromNotifications();
      if (success) {
        setSuccessMessage('Push notifications disabled successfully');
        await fetchNotificationSummary();
      } else {
        setError('Failed to disable notifications');
      }
    } catch (err: any) {
      console.error('Failed to disable notifications:', err);
      setError(err.message || 'Failed to disable notifications');
    } finally {
      setDisabling(false);
    }
  };

  const handleSendTestNotification = async () => {
    setTesting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await NotificationService.sendTestNotification();
      setSuccessMessage('Test notification sent! Check your notifications.');
    } catch (err: any) {
      console.error('Failed to send test notification:', err);
      setError(err.message || 'Failed to send test notification');
    } finally {
      setTesting(false);
    }
  };

  const getPermissionIcon = () => {
    switch (summary.permission) {
      case 'granted':
        return (
          <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case 'denied':
        return (
          <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
    }
  };

  const getStatusText = () => {
    if (!summary.supported) return 'Not supported in this browser';
    if (summary.permission === 'denied') return 'Blocked - Please enable in browser settings';
    if (summary.permission === 'granted' && summary.subscribed) return 'Enabled';
    return 'Disabled';
  };

  const getStatusColor = () => {
    if (!summary.supported || summary.permission === 'denied') return 'text-red-400';
    if (summary.permission === 'granted' && summary.subscribed) return 'text-green-400';
    return 'text-gray-400';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-800 rounded-xl shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM9 6H4l5-5v5zM12 2v20" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white">Daily Reminders</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-flex items-center gap-3 text-gray-400">
                <div className="w-5 h-5 border-2 border-gray-600 border-t-orange-500 rounded-full animate-spin" />
                <span>Loading notification settings...</span>
              </div>
            </div>
          ) : (
            <>
              {/* Status Section */}
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getPermissionIcon()}
                    <div>
                      <h4 className="text-sm font-medium text-white">Notification Status</h4>
                      <p className={`text-sm ${getStatusColor()}`}>{getStatusText()}</p>
                    </div>
                  </div>
                  {summary.deviceCount > 0 && (
                    <div className="text-right">
                      <p className="text-xs text-gray-400">Active devices</p>
                      <p className="text-lg font-semibold text-orange-500">{summary.deviceCount}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Description */}
              <div className="text-gray-300 text-sm leading-relaxed">
                <p className="mb-2">
                  Get reminded of your notes every day at <strong className="text-orange-400">10:00 AM IST</strong>.
                </p>
                <p>
                  We'll cycle through your notes in a round-robin fashion, so you'll see different notes each day.
                </p>
              </div>

              {/* Error/Success Messages */}
              {error && (
                <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-3">
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              )}
              
              {successMessage && (
                <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-3">
                  <p className="text-green-300 text-sm">{successMessage}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3">
                {!summary.supported ? (
                  <div className="text-center py-4">
                    <p className="text-gray-400 text-sm">
                      Push notifications are not supported in this browser.
                    </p>
                  </div>
                ) : summary.permission === 'denied' ? (
                  <div className="text-center py-4">
                    <p className="text-gray-400 text-sm mb-3">
                      Notifications are blocked. Please enable them in your browser settings.
                    </p>
                    <button
                      onClick={() => window.location.reload()}
                      className="text-orange-400 hover:text-orange-300 text-sm underline"
                    >
                      Reload page after enabling
                    </button>
                  </div>
                ) : (
                  <>
                    {summary.subscribed ? (
                      <>
                        <button
                          onClick={handleDisableNotifications}
                          disabled={disabling}
                          className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-3 rounded-lg transition-colors duration-200"
                        >
                          {disabling ? (
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              <span>Disabling...</span>
                            </div>
                          ) : (
                            'Disable Notifications'
                          )}
                        </button>
                        
                        <button
                          onClick={handleSendTestNotification}
                          disabled={testing}
                          className="w-full bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-3 rounded-lg transition-colors duration-200"
                        >
                          {testing ? (
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              <span>Sending...</span>
                            </div>
                          ) : (
                            'Send Test Notification'
                          )}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={handleEnableNotifications}
                        disabled={enabling}
                        className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-3 rounded-lg transition-colors duration-200"
                      >
                        {enabling ? (
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>Enabling...</span>
                          </div>
                        ) : (
                          'Enable Daily Reminders'
                        )}
                      </button>
                    )}
                  </>
                )}
              </div>

              {/* Help Text */}
              <div className="text-xs text-gray-500 text-center pt-2">
                Notifications work across all your devices where you're logged in
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationSettings;