/**
 * Valora AI - Multi-Tenant RBAC Configuration
 * 
 * 3-Way Segment Split:
 * ┌─────────────────────────────────────────────────────────────────────┐
 * │  BROKER 👉 Execution Layer                                           │
 * │      Deals, clients, listings, workflows. High frequency.             │
 * │                                                                   │
 * │  BUYER 👉 Individual Decision Layer                                │
 * │      Home buyers, investors, NRI. Personal decisions.              │
 * │      Can also SELL properties (intent: sell/both)                  │
 * │                                                                   │
 * │  DEVELOPER 👉 Institutional Decision Layer                       │
 * │      Project planning, land acquisition, pricing.                  │
 * └─────────────────────────────────────────────────────────────────────┘
 * 
 * Intent (NOT a separate role):
 * - buy: Looking to purchase property
 * - sell: Want to list and sell property
 * - both: Buy and sell - complete transactions
 * 
 * Seller is an intent, not an identity.
 * Multi-Tenant Architecture with isolation.
 */

// Layer 1: Identity Roles (set at signup)
export const IDENTITY_ROLES = {
  BROKER: 'broker',
  DEVELOPER: 'developer',
  BUYER: 'buyer',
  ADMIN: 'admin', // hidden internal
  VALORA_TEAM: 'valora-team', // hidden internal
};

export const IDENTITY_LABELS = {
  [IDENTITY_ROLES.BROKER]: 'Broker',
  [IDENTITY_ROLES.DEVELOPER]: 'Developer',
  [IDENTITY_ROLES.BUYER]: 'Buyer',
  [IDENTITY_ROLES.ADMIN]: 'Admin',
  [IDENTITY_ROLES.VALORA_TEAM]: 'Valora Team',
};

// Hidden internal roles (not shown in signup)
export const INTERNAL_ROLES = [IDENTITY_ROLES.ADMIN, IDENTITY_ROLES.VALORA_TEAM];

// Intent (WHAT user wants to do)
export const INTENTS = {
  BUY: 'buy',
  SELL: 'sell',
  BOTH: 'both',
};

export const INTENT_LABELS = {
  [INTENTS.BUY]: 'Buy',
  [INTENTS.SELL]: 'Sell',
  [INTENTS.BOTH]: 'Buy & Sell',
};

// Seller features enabled if intent is 'sell' or 'both'
export function hasSellerFeatures(intent) {
  return intent === INTENTS.SELL || intent === INTENTS.BOTH;
}

// Layer 2: Workspace Types
export const WORKSPACE_TYPES = {
  INDIVIDUAL: 'individual',
  TEAM: 'team',
};

export const WORKSPACE_LABELS = {
  [WORKSPACE_TYPES.INDIVIDUAL]: 'Individual',
  [WORKSPACE_TYPES.TEAM]: 'Team',
};

// Layer 3: Workspace Roles (only in Team workspaces)
export const WORKSPACE_ROLES = {
  MANAGER: 'manager',
  MEMBER: 'member',
};

export const WORKSPACE_ROLE_LABELS = {
  [WORKSPACE_ROLES.MANAGER]: 'Manager',
  [WORKSPACE_ROLES.MEMBER]: 'Member',
};

// Layer 4: Subscription Plans
export const SUBSCRIPTION_PLANS = {
  FREE: 'free',
  PRO: 'pro',
  TEAM: 'team',
};

export const PLAN_LABELS = {
  [SUBSCRIPTION_PLANS.FREE]: 'Free',
  [SUBSCRIPTION_PLANS.PRO]: 'Pro',
  [SUBSCRIPTION_PLANS.TEAM]: 'Team',
};

// AI Personas (determined by Identity Layer)
export const AI_PERSONAS = {
  BROKER_AI: 'broker-ai',
  DEVELOPER_AI: 'developer-ai',
  BUYER_AI: 'buyer-ai',
};

export const AI_PERSONA_CONFIG = {
  [AI_PERSONAS.BROKER_AI]: {
    name: 'Broker AI',
    focus: 'Deals, clients, listings, workflows. High frequency executions.',
    tone: 'execution',
    dashboardWidgets: ['alerts', 'tasks', 'leads', 'quickActions', 'smartReports'],
  },
  [AI_PERSONAS.DEVELOPER_AI]: {
    name: 'Developer AI',
    focus: 'Project planning, land acquisition, pricing intelligence, demand density.',
    tone: 'institutional',
    dashboardWidgets: ['marketSentiment', 'pricingAnalytics', 'demandDensity', 'competitorAnalysis'],
  },
  [AI_PERSONAS.BUYER_AI]: {
    name: 'Buyer AI',
    focus: 'Home buyers, investors, NRI. Personal decisions, report-driven.',
    tone: 'advisory',
    dashboardWidgets: ['roiAnalysis', 'riskAssessment', 'localityDeepDive', 'familyCollaboration'],
  },
};

// Feature flags by plan
export const PLAN_FEATURES = {
  [SUBSCRIPTION_PLANS.FREE]: {
    maxAlerts: 3,
    maxScheduledTasks: 5,
    smartTabs: ['free'],
    pdfExport: false,
    teamManagement: false,
    emailChannel: false,
    autoExecution: false,
  },
  [SUBSCRIPTION_PLANS.PRO]: {
    maxAlerts: Infinity,
    maxScheduledTasks: Infinity,
    smartTabs: ['free', 'comparables', 'investment', 'roi', 'market', 'legal', 'vastu', 'schools', 'transport'],
    pdfExport: true,
    teamManagement: false,
    emailChannel: true,
    autoExecution: true,
  },
  [SUBSCRIPTION_PLANS.TEAM]: {
    maxAlerts: Infinity,
    maxScheduledTasks: Infinity,
    smartTabs: ['free', 'comparables', 'investment', 'roi', 'market', 'legal', 'vastu', 'schools', 'transport'],
    pdfExport: true,
    teamManagement: true,
    emailChannel: true,
    autoExecution: true,
  },
};

// Workspace permissions
export const WORKSPACE_PERMISSIONS = {
  [WORKSPACE_ROLES.MANAGER]: {
    manageMembers: true,
    changePlan: true,
    viewAllData: true,
    viewWorkspaceData: true,
    viewOwnData: true,
    viewPublicData: true,
    createSharedResources: true,
    exportReports: true,
    deleteSharedResources: true,
  },
  [WORKSPACE_ROLES.MEMBER]: {
    manageMembers: false,
    changePlan: false,
    viewAllData: true,
    viewWorkspaceData: true,
    viewOwnData: true,
    viewPublicData: true,
    createSharedResources: true,
    exportReports: true,
    deleteSharedResources: false,
  },
};

// Data isolation by identity role
// Prevents cross-user data leakage between segments
export const IDENTITY_DATA_ISOLATION = {
  [IDENTITY_ROLES.BROKER]: {
    leadsScope: 'workspace', // Can only see leads in same workspace
    alertsScope: 'workspace',
    reportsScope: 'workspace',
    marketDataScope: 'public', // Can see public market data
    competitorDataScope: 'none', // Cannot see competitor data ❌
    propertyAccessScope: 'public', // Public listings only unless shared
  },
  [IDENTITY_ROLES.DEVELOPER]: {
    leadsScope: 'org', // Can see org-level data
    alertsScope: 'org',
    reportsScope: 'org',
    marketDataScope: 'full', // Can see market trends
    competitorDataScope: 'none', // Cannot see competitor data ❌
    propertyAccessScope: 'public',
  },
  [IDENTITY_ROLES.BUYER]: {
    leadsScope: 'family', // Family hub only
    alertsScope: 'own',
    reportsScope: 'own',
    marketDataScope: 'full', // Can see market data for decisions
    competitorDataScope: 'none', // N/A for buyers
    propertyAccessScope: 'public',
  },
};

// Helper function to check data access
export function canViewData(dataType, identityRole, workspaceType, isOwner = false, isInWorkspace = false) {
  const isolation = IDENTITY_DATA_ISOLATION[identityRole] || IDENTITY_DATA_ISOLATION[IDENTITY_ROLES.BUYER];
  
  switch (dataType) {
    case 'leads':
      if (isolation.leadsScope === 'workspace') return isInWorkspace;
      if (isolation.leadsScope === 'org') return workspaceType === 'team';
      if (isolation.leadsScope === 'own') return isOwner;
      return false;
      
    case 'alerts':
      if (isolation.alertsScope === 'workspace') return isInWorkspace;
      if (isolation.alertsScope === 'org') return workspaceType === 'team';
      if (isolation.alertsScope === 'own') return isOwner;
      return false;
      
    case 'reports':
      if (isolation.reportsScope === 'workspace') return isInWorkspace;
      if (isolation.reportsScope === 'org') return workspaceType === 'team';
      if (isolation.reportsScope === 'own') return isOwner;
      return false;
      
    case 'competitor':
      // Always deny competitor data ❌
      return isolation.competitorDataScope !== 'none' && workspaceType === 'team';
      
    case 'market':
      return isolation.marketDataScope === 'public' || isolation.marketDataScope === 'full';
      
    default:
      return isolation.propertyAccessScope === 'public';
  }
}

// Helper to get AI persona from identity role
export function getAIPersona(identityRole) {
  switch (identityRole) {
    case IDENTITY_ROLES.BROKER:
      return AI_PERSONAS.BROKER_AI;
    case IDENTITY_ROLES.DEVELOPER:
      return AI_PERSONAS.DEVELOPER_AI;
    case IDENTITY_ROLES.BUYER:
      return AI_PERSONAS.BUYER_AI;
    default:
      return AI_PERSONAS.BROKER_AI;
  }
}

// Helper to check if role is internal
export function isInternalRole(role) {
  return INTERNAL_ROLES.includes(role);
}

// Helper to get user permissions
export function getUserPermissions(workspaceType, workspaceRole, plan) {
  const features = PLAN_FEATURES[plan] || PLAN_FEATURES[SUBSCRIPTION_PLANS.FREE];
  
  if (workspaceType === WORKSPACE_TYPES.INDIVIDUAL) {
    return {
      ...features,
      ...WORKSPACE_PERMISSIONS[WORKSPACE_ROLES.MANAGER], // Individual owner has full permissions
      isManager: true,
    };
  }
  
  return {
    ...features,
    ...WORKSPACE_PERMISSIONS[workspaceRole || WORKSPACE_ROLES.MEMBER],
    isManager: workspaceRole === WORKSPACE_ROLES.MANAGER,
  };
}

// Default values for new users
export const DEFAULT_USER_CONFIG = {
  identityRole: IDENTITY_ROLES.BROKER,
  workspaceType: WORKSPACE_TYPES.INDIVIDUAL,
  workspaceRole: WORKSPACE_ROLES.MANAGER,
  plan: SUBSCRIPTION_PLANS.FREE,
  aiPersona: AI_PERSONAS.BROKER_AI,
};

// ============================================================
// MULTI-TENANT ISOLATION FUNCTIONS
// ============================================================

/**
 * Get tenant identifier for a user
 * - Individual: user_id as tenant_id
 * - Team: workspace_id as tenant_id
 */
export function getTenantId(user) {
  if (!user) return null;
  
  const workspaceType = user.workspaceType || user.workspace_type;
  
  if (workspaceType === WORKSPACE_TYPES.TEAM) {
    return user.workspaceId || user.workspace_id || `ws_${user.id}`;
  }
  
  return `user_${user.id}`;
}

/**
 * Get tenant scope for query filtering
 * All database queries MUST include tenant_id filter
 */
export function getTenantScope(user) {
  const workspaceType = user?.workspaceType || user?.workspace_type;
  const workspaceRole = user?.workspaceRole || user?.workspace_role;
  
  return {
    tenantId: getTenantId(user),
    canViewAll: workspaceRole === WORKSPACE_ROLES.MANAGER,
    canViewShared: workspaceType === WORKSPACE_TYPES.TEAM,
    scope: workspaceType === WORKSPACE_TYPES.TEAM ? 'workspace' : 'own',
  };
}

/**
 * Build tenant filter for SQL queries
 * Use in ALL queries to prevent data leakage
 */
export function buildTenantFilter(user, tableAlias = '') {
  const scope = getTenantScope(user);
  const alias = tableAlias ? `${tableAlias}.` : '';
  
  if (scope.scope === 'workspace') {
    return `${alias}tenant_id = '${scope.tenantId}'`;
  }
  
  return `${alias}user_id = '${scope.tenantId}'`;
}

/**
 * Check if user can access specific data resource
 */
export function canAccessResource(resource, user, ownerId) {
  const scope = getTenantScope(user);
  const identityRole = user?.job_role || user?.identityRole;
  
  // Owner can always access own data
  if (ownerId === user?.id) return true;
  
  // Check workspace membership for team workspaces
  if (scope.scope === 'workspace' && scope.canViewShared) {
    return true; // Team member can access shared workspace data
  }
  
  return false;
}

/**
 * Filter object to remove cross-tenant fields
 * Use before sending to client
 */
export function filterTenantData(data, user) {
  const scope = getTenantScope(user);
  
  // Remove fields that shouldn't be visible
  const filtered = { ...data };
  
  // Remove other tenant info if strict isolation
  delete filtered.other_tenants;
  delete filtered.competitor_data;
  delete filtered.cross_workspace_data;
  
  return filtered;
}