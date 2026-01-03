export interface NodeMetadata {
  id: string;
  name: string;
  host: string;
  api_port: number;
  node_name: string;
  mac_address?: string;
  [key: string]: unknown;
}

export interface NodeState {
  label: string;
  variant: "ok" | "warn" | "error" | string;
  online: boolean;
}

export interface NodeGuests {
  kvm: number;
  lxc: number;
  total: number;
}

export interface NodeMetrics {
  uptime: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  memory_summary: string;
  load: string;
  guests: NodeGuests;
}

export interface NodeSnapshot {
  id: string;
  name: string;
  meta: NodeMetadata;
  state: NodeState;
  metrics: NodeMetrics;
  error?: {
    message?: string;
    code?: number;
  } | null;
  checked_at?: string;
}

export interface DashboardEvent {
  tone: "info" | "warn" | "danger" | string;
  title: string;
  body: string;
  timestamp?: string;
  clock?: string;
  node?: string;
}

export interface DashboardPayload {
  generated_at: string;
  nodes: NodeSnapshot[];
  events: DashboardEvent[];
}
