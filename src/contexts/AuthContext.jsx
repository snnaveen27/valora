import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_URL } from '../apiConfig';
import { 
  IDENTITY_ROLES, 
  WORKSPACE_TYPES, 
  WORKSPACE_ROLES, 
  SUBSCRIPTION_PLANS, 
  getUserPermissions,
  getAIPersona,
  PLAN_FEATURES,
  AI_PERSONAS
} from '../config/roles';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load saved auth on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('valora_token');
    const savedUser = localStorage.getItem('valora_user');
    
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      // Verify token is still valid
      verifyToken(savedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyToken = async (tokenToVerify) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/verify`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokenToVerify}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        localStorage.setItem('valora_user', JSON.stringify(data.user));
      } else {
        // Token invalid, clear auth
        logout();
      }
    } catch (err) {
      console.error('Token verification failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    setError(null);
    setLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('valora_token', data.access_token);
      localStorage.setItem('valora_user', JSON.stringify(data.user));
      
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const signup = async (email, password, name, company = '', phone = '', job_role = '', workspace_type = 'individual', workspace_role = 'manager') => {
    setError(null);
    setLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/api/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name, company, phone, job_role, workspace_type, workspace_role }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed');
      }
      
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('valora_token', data.access_token);
      localStorage.setItem('valora_user', JSON.stringify(data.user));
      
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('valora_token');
    localStorage.removeItem('valora_user');
  }, []);

  const updateProfile = async (updates) => {
    if (!token) return { success: false, error: 'Not authenticated' };
    
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Update failed');
      }
      
      setUser(data);
      localStorage.setItem('valora_user', JSON.stringify(data));
      
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    if (!token) return { success: false, error: 'Not authenticated' };
    
    try {
      const response = await fetch(`${API_URL}/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          current_password: currentPassword, 
          new_password: newPassword 
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Password change failed');
      }
      
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const getUsage = async () => {
    if (!token) return null;
    
    try {
      const response = await fetch(`${API_URL}/api/auth/usage`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.error('Failed to get usage:', err);
    }
    return null;
  };

  // Check if user has feature access based on RBAC permissions
  const hasFeature = (feature) => {
    if (!user) return false;
    // Use backend tier_limits as fallback, otherwise use RBAC permissions
    if (user.tier_limits?.features) {
      const tierFeatures = user.tier_limits.features || [];
      return tierFeatures.includes(feature) || tierFeatures.includes('all_features');
    }
    // Use RBAC permissions from config
    return planFeatures[feature] === true || planFeatures[feature] === undefined;
  };

  // Check query limit
  const canQuery = () => {
    if (!user) return false;
    const limit = user.tier_limits?.queries_per_day || 0;
    if (limit === -1) return true; // Unlimited
    return user.queries_today < limit;
  };

  // RBAC derived values
  const identityRole = user?.job_role || IDENTITY_ROLES.BROKER
  const workspaceType = user?.workspaceType || user?.workspace_type || WORKSPACE_TYPES.INDIVIDUAL
  const workspaceRole = user?.workspaceRole || user?.workspace_role || WORKSPACE_ROLES.MANAGER
  const plan = user?.tier || user?.plan || SUBSCRIPTION_PLANS.FREE
  const aiPersona = getAIPersona(identityRole)
  const permissions = getUserPermissions(workspaceType, workspaceRole, plan)
  const planFeatures = PLAN_FEATURES[plan] || PLAN_FEATURES[SUBSCRIPTION_PLANS.FREE]

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    // RBAC layers
    identityRole,
    workspaceType,
    workspaceRole,
    plan,
    aiPersona,
    permissions,
    isManager: workspaceRole === WORKSPACE_ROLES.MANAGER,
    isTeam: workspaceType === WORKSPACE_TYPES.TEAM,
    login,
    signup,
    logout,
    updateProfile,
    changePassword,
    getUsage,
    hasFeature,
    canQuery,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
