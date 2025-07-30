import React, { useState } from 'react';

interface Agent {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy';
  activeChats: number;
  totalChats: number;
  avgResponseTime: string;
  lastSeen: string;
}

const AgentDashboard: React.FC = () => {
  const [agents] = useState<Agent[]>([
    {
      id: '1',
      name: 'Support Bot',
      status: 'online',
      activeChats: 8,
      totalChats: 234,
      avgResponseTime: '1.2s',
      lastSeen: 'Now',
    },
    {
      id: '2',
      name: 'Sales Assistant',
      status: 'online',
      activeChats: 12,
      totalChats: 189,
      avgResponseTime: '2.1s',
      lastSeen: 'Now',
    },
    {
      id: '3',
      name: 'Technical Support',
      status: 'busy',
      activeChats: 15,
      totalChats: 156,
      avgResponseTime: '3.4s',
      lastSeen: '2 min ago',
    },
    {
      id: '4',
      name: 'Customer Care',
      status: 'offline',
      activeChats: 0,
      totalChats: 98,
      avgResponseTime: '2.8s',
      lastSeen: '1 hour ago',
    },
  ]);

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'busy':
        return 'bg-yellow-500';
      case 'offline':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusTextColor = (status: Agent['status']) => {
    switch (status) {
      case 'online':
        return 'text-green-600 dark:text-green-400';
      case 'busy':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'offline':
        return 'text-gray-600 dark:text-gray-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Agent Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Online Agents</span>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {agents.filter(a => a.status === 'online').length}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Busy Agents</span>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {agents.filter(a => a.status === 'busy').length}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Total Active Chats</span>
          </div>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {agents.reduce((sum, agent) => sum + agent.activeChats, 0)}
          </p>
        </div>
      </div>

      {/* Agents Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Agent Status</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Active Chats
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Total Chats
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Avg Response
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Last Seen
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {agents.map((agent) => (
                <tr key={agent.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center mr-3">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {agent.name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {agent.name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          ID: {agent.id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-2 ${getStatusColor(agent.status)}`}></div>
                      <span className={`text-sm font-medium capitalize ${getStatusTextColor(agent.status)}`}>
                        {agent.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {agent.activeChats}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {agent.totalChats}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {agent.avgResponseTime}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {agent.lastSeen}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300">
                        View
                      </button>
                      <button className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300">
                        Monitor
                      </button>
                      <button className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300">
                        Stop
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;