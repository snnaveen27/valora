/**
 * DashboardRouter - Routes to the correct dashboard based on user identity role.
 * 
 * Identity roles:
 * - broker     → BrokerDashboard
 * - developer  → DeveloperDashboard
 * - buyer      → BuyerDashboard
 * - admin      → All three dashboards (tabbed view)
 * - valora-team → All three dashboards (tabbed view)
 */

import { useState } from 'react';
import BrokerDashboard from './BrokerDashboard';
import DeveloperDashboard from './DeveloperDashboard';
import BuyerDashboard from './BuyerDashboard';
import { useAuth } from '../contexts/AuthContext';
import { IDENTITY_ROLES } from '../config/roles';
import { Users, Building2, Home } from 'lucide-react';

const DASHBOARD_CONFIG = {
  [IDENTITY_ROLES.BROKER]: {
    component: BrokerDashboard,
    label: 'Broker',
    icon: Users,
    color: 'text-blue-400',
  },
  [IDENTITY_ROLES.DEVELOPER]: {
    component: DeveloperDashboard,
    label: 'Developer',
    icon: Building2,
    color: 'text-purple-400',
  },
  [IDENTITY_ROLES.BUYER]: {
    component: BuyerDashboard,
    label: 'Buyer',
    icon: Home,
    color: 'text-emerald-400',
  },
};

const ADMIN_TABS = [
  { role: IDENTITY_ROLES.BROKER, label: 'Broker', icon: Users, color: 'text-blue-400', activeColor: 'from-blue-500 to-cyan-500' },
  { role: IDENTITY_ROLES.DEVELOPER, label: 'Developer', icon: Building2, color: 'text-purple-400', activeColor: 'from-purple-500 to-pink-500' },
  { role: IDENTITY_ROLES.BUYER, label: 'Buyer', icon: Home, color: 'text-emerald-400', activeColor: 'from-emerald-500 to-green-500' },
];

export default function DashboardRouter(props) {
  const { user } = useAuth();
  const [adminTab, setAdminTab] = useState(IDENTITY_ROLES.BROKER);

  const role = user?.job_role || user?.role || IDENTITY_ROLES.BROKER;
  const isAdmin = role === IDENTITY_ROLES.ADMIN || role === IDENTITY_ROLES.VALORA_TEAM;

  if (isAdmin) {
    const ActiveDashboard = DASHBOARD_CONFIG[adminTab]?.component || BrokerDashboard;

    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-700/50 bg-slate-800/30">
          {ADMIN_TABS.map(tab => {
            const isActive = adminTab === tab.role;
            const Icon = tab.icon;
            return (
              <button
                key={tab.role}
                onClick={() => setAdminTab(tab.role)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? `bg-gradient-to-r ${tab.activeColor} text-white shadow-lg`
                    : `${tab.color} hover:bg-slate-700/40`
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto">
          <ActiveDashboard {...props} />
        </div>
      </div>
    );
  }

  const config = DASHBOARD_CONFIG[role] || DASHBOARD_CONFIG[IDENTITY_ROLES.BROKER];
  const DashboardComponent = config.component;

  return <DashboardComponent {...props} />;
}
