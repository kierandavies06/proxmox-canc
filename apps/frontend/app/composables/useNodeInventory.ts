import type { NodeMetadata } from "~/types/dashboard";

export function useNodeInventory() {
  const config = useRuntimeConfig();
  const baseUrl = process.server
    ? config.apiBaseUrl
    : config.public.apiBaseUrl || config.apiBaseUrl;

  return useAsyncData(
    "node-inventory",
    () =>
      $fetch<NodeMetadata[]>(`${baseUrl}/api/nodes`, {
        timeout: 5_000,
      }),
    {
      server: false,
      default: () => [],
    },
  );
}
