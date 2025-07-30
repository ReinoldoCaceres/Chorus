import React from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

const Dashboard: React.FC = () => {
  const { isConnected, connectionError } = useWebSocket();

  const stats = [
    { label: 'Active Agents', value: 12, change: '+2 from yesterday', changeType: 'positive' },
    { label: 'Total Chats', value: 1234, change: '+15% from last week', changeType: 'positive' },
    { label: 'Avg Response Time', value: '2.3s', change: '-0.5s from yesterday', changeType: 'positive' },
    { label: 'Success Rate', value: '98.5%', change: '+0.2% from yesterday', changeType: 'positive' },
  ];

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <div className={`p-4 rounded-lg ${
        isConnected 
          ? 'bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700' 
          : 'bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700'
      }`}>
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full mr-2 ${
            isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          }`}></div>
          <span className={`font-medium ${
            isConnected ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'
          }`}>
            {isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
          </span>
          {connectionError && (
            <span className="ml-2 text-sm text-red-600 dark:text-red-300">
              - {connectionError}
            </span>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{stat.value}</p>
              </div>
            </div>
            <div className="mt-4">
              <span className={`text-sm ${
                stat.changeType === 'positive' 
                  ? 'text-green-600 dark:text-green-400' 
                  : 'text-red-600 dark:text-red-400'
              }`}>
                {stat.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {[
              { time: '2 min ago', event: 'Agent "Support Bot" handled 5 new conversations', type: 'info' },
              { time: '15 min ago', event: 'New agent "Sales Assistant" came online', type: 'success' },
              { time: '1 hour ago', event: 'Peak traffic detected - 150 concurrent users', type: 'warning' },
              { time: '2 hours ago', event: 'Daily backup completed successfully', type: 'info' },
            ].map((activity, index) => (
              <div key={index} className="flex items-start space-x-3">
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  activity.type === 'success' ? 'bg-green-500' :
                  activity.type === 'warning' ? 'bg-yellow-500' :
                  'bg-blue-500'
                }`}></div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900 dark:text-white">{activity.event}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;