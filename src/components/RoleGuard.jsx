/**
 * RoleGuard - Role-Based Access Control Component
 * 
 * Used to protect routes or UI features based on:
 * - Identity role (broker/developer/buyer)
 * - Workspace type (individual/team)
 * - Workspace role (manager/member)
 * - Plan (free/pro/team)
 * - Specific permissions
 */

import { useAuth } from '../contexts/AuthContext'
import { IDENTITY_ROLES, WORKSPACE_TYPES, WORKSPACE_ROLES, SUBSCRIPTION_PLANS, getUserPermissions } from '../config/roles'

/**
 * RoleGuard - Protect children based on RBAC rules
 * @param {Object} props
 * @param {string|string[]} props.allowRoles - Identity roles to allow (broker/developer/buyer)
 * @param {string|string[]} props.allowWorkspaces - Workspace types to allow (individual/team)
 * @param {string|string[]} props.allowPermissions - Permissions required
 * @param {string|string[]} props.denyRoles - Identity roles to deny
 * @param {boolean} props.allowInternal - Allow internal roles (admin, valora-team)
 * @param {React.ReactNode} props.fallback - Fallback UI when access denied
 * @param {React.ReactNode} props.children - Protected content
 */
export default function RoleGuard({
  allowRoles,
  allowWorkspaces,
  allowPermissions,
  denyRoles,
  allowInternal = false,
  fallback = null,
  children
}) {
  const { user } = useAuth()
  
  if (!user) {
    return fallback
  }

  // Get actual values from user (may come from backend or onboarding)
  const identityRole = user.job_role || user.identityRole || IDENTITY_ROLES.BROKER
  const workspaceType = user.workspaceType || user.workspace_type || WORKSPACE_TYPES.INDIVIDUAL
  const workspaceRole = user.workspaceRole || user.workspace_role || WORKSPACE_ROLES.MANAGER
  const plan = user.tier || user.plan || SUBSCRIPTION_PLANS.FREE

  // Check deny roles first
  if (denyRoles) {
    const denyList = Array.isArray(denyRoles) ? denyRoles : [denyRoles]
    if (denyList.includes(identityRole)) {
      return fallback
    }
  }

  // Check allowed roles
  if (allowRoles && !allowInternal) {
    const allowList = Array.isArray(allowRoles) ? allowRoles : [allowRoles]
    
    // Check if internal role trying to access (only allow if explicitly in list)
    const isInternalRole = identityRole === IDENTITY_ROLES.ADMIN || identityRole === IDENTITY_ROLES.VALORA_TEAM
    
    if (isInternalRole && !allowList.includes(identityRole)) {
      return fallback
    }
    
    if (!allowList.includes(identityRole)) {
      return fallback
    }
  }

  // Check workspace type
  if (allowWorkspaces) {
    const workspaceList = Array.isArray(allowWorkspaces) ? allowWorkspaces : [allowWorkspaces]
    if (!workspaceList.includes(workspaceType)) {
      return fallback
    }
  }

  // Check permissions
  if (allowPermissions) {
    const permissions = getUserPermissions(workspaceType, workspaceRole, plan)
    const requiredPerms = Array.isArray(allowPermissions) ? allowPermissions : [allowPermissions]
    
    for (const perm of requiredPerms) {
      if (!permissions[perm]) {
        return fallback
      }
    }
  }

  return children
}

/**
 * useRoleAccess - Hook to check role permissions programmatically
 * @returns {Object} - { hasAccess, identityRole, workspaceType, workspaceRole, plan, permissions }
 */
export function useRoleAccess() {
  const { user } = useAuth()
  
  const identityRole = user?.job_role || user?.identityRole || IDENTITY_ROLES.BROKER
  const workspaceType = user?.workspaceType || user?.workspace_type || WORKSPACE_TYPES.INDIVIDUAL
  const workspaceRole = user?.workspaceRole || user?.workspace_role || WORKSPACE_ROLES.MANAGER
  const plan = user?.tier || user?.plan || SUBSCRIPTION_PLANS.FREE
  const permissions = getUserPermissions(workspaceType, workspaceRole, plan)
  
  return {
    hasAccess: !!user,
    identityRole,
    workspaceType,
    workspaceRole,
    plan,
    isManager: workspaceRole === WORKSPACE_ROLES.MANAGER,
    isTeam: workspaceType === WORKSPACE_TYPES.TEAM,
    permissions,
  }
}

/**
 * HOC to wrap component with role protection
 * @param {React.Component} Component - Component to wrap
 * @param {Object} options - RBAC options
 * @returns {React.Component} - Wrapped component
 */
export function withRoleAccess(Component, options) {
  return function ProtectedComponent(props) {
    return (
      <RoleGuard {...options}>
        <Component {...props} />
      </RoleGuard>
    )
  }
}