import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, FilePlus, FileText, Activity, Clock, ShieldAlert, FastForward } from 'lucide-react';

const Layout = ({ children }) => {
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Simulation', path: '/simulation', icon: FastForward },
    { name: 'Submit Claim', path: '/submit', icon: FilePlus },
    { name: 'Claims', path: '/claims', icon: FileText },
    { name: 'Model Performance', path: '/performance', icon: Activity },
    { name: 'Simulator', path: '/simulator', icon: Clock },
  ];

  const getPageTitle = () => {
    const current = navItems.find((item) => item.path === location.pathname);
    if (current) return current.name;
    if (location.pathname.startsWith('/claims/')) return 'Claim Details';
    return 'Dashboard';
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col shadow-xl z-10">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <ShieldAlert className="w-8 h-8 text-indigo-500 mr-3" />
          <span className="text-xl font-bold tracking-wide">ClaimGuard</span>
        </div>
        <nav className="flex-1 py-6 px-4 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 shadow-sm z-0">
          <h1 className="text-2xl font-semibold text-slate-800">{getPageTitle()}</h1>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50 p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
