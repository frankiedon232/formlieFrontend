/**
 * Mock tenants, organisations and users (in memory; signup adds to them).
 * Test sign-in for every seeded user — mock only, never a real credential:
 *   password  Formalie!2026
 *   OTP       shown on the code screen in dev (mock returns `dev_code`) and logged to the server console
 */
import type { AuthProvider, TenantStatus } from '#shared/types/auth'

export const MOCK_PASSWORD = 'Formalie!2026'

export interface MockTenant {
  id: string
  name: string
  subdomain: string
  status: TenantStatus
  auth_providers: AuthProvider[]
  organisation: { id: string; name: string }
}

export interface MockUser {
  id: string
  tenant_id: string
  first_name: string
  last_name: string
  email: string
  password: string
  phone: string | null
  disabled: boolean
}

export const MOCK_TENANTS: MockTenant[] = [
  {
    id: '6f0e2a14-3c2b-4d55-9a0f-1b2c3d4e5f60',
    name: 'Remedy Legal',
    subdomain: 'remedylegal',
    status: 'active',
    auth_providers: ['password', 'google', 'microsoft'],
    organisation: { id: '0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d', name: 'Remedy Legal' },
  },
  {
    id: '7a1f3b25-4d3c-4e66-8b10-2c3d4e5f6071',
    name: 'Samath Tax',
    subdomain: 'samathtax',
    status: 'active',
    auth_providers: ['password', 'google', 'apple', 'facebook'],
    organisation: { id: '1b2c3d4e-5f60-4b7c-9d8e-0f1a2b3c4d5e', name: 'Samath Tax Lagos' },
  },
  {
    id: '8b2a4c36-5e4d-4f77-9c21-3d4e5f607182',
    name: 'Old Co',
    subdomain: 'oldco',
    status: 'suspended',
    auth_providers: ['password'],
    organisation: { id: '2c3d4e5f-6071-4c8d-8e9f-1a2b3c4d5e6f', name: 'Old Co' },
  },
]

export const MOCK_USERS: MockUser[] = [
  {
    id: 'a1b2c3d4-0001-4000-8000-000000000001',
    tenant_id: MOCK_TENANTS[0]!.id,
    first_name: 'Frankie',
    last_name: 'Don',
    email: 'admin@remedylegal.test',
    password: MOCK_PASSWORD,
    phone: '+2348000000001',
    disabled: false,
  },
  {
    id: 'a1b2c3d4-0002-4000-8000-000000000002',
    tenant_id: MOCK_TENANTS[1]!.id,
    first_name: 'Amaka',
    last_name: 'Obi',
    email: 'admin@samathtax.test',
    password: MOCK_PASSWORD,
    phone: null,
    disabled: false,
  },
  {
    // Same person in two workspaces → "find my workspace" lists both.
    id: 'a1b2c3d4-0003-4000-8000-000000000003',
    tenant_id: MOCK_TENANTS[1]!.id,
    first_name: 'Frankie',
    last_name: 'Don',
    email: 'admin@remedylegal.test',
    password: MOCK_PASSWORD,
    phone: null,
    disabled: false,
  },
  {
    id: 'a1b2c3d4-0004-4000-8000-000000000004',
    tenant_id: MOCK_TENANTS[0]!.id,
    first_name: 'Disabled',
    last_name: 'User',
    email: 'disabled@remedylegal.test',
    password: MOCK_PASSWORD,
    phone: null,
    disabled: true,
  },
]
