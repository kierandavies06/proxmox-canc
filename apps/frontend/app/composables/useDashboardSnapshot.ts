import type { DashboardPayload } from "~/types/dashboard";

const FALLBACK_STATE: DashboardPayload = {
  generated_at: "",
  nodes: [],
  events: [],
};

export function useDashboardSnapshot() {
  const config = useRuntimeConfig();
  const baseUrl = process.server
    ? config.apiBaseUrl
    : config.public.apiBaseUrl || config.apiBaseUrl;

  const { data, pending, error, refresh } = useAsyncData(
    "dashboard-snapshot",
    () =>
      $fetch<DashboardPayload>(`${baseUrl}/api/dashboard`, {
        timeout: 7_000,
      }),
    {
      server: false,
      default: () => FALLBACK_STATE,
      lazy: true,
    },
  );

  const timer = useState<number | null>("dashboard-refresh-timer", () => null);

  onMounted(() => {
    if (timer.value) {
      clearInterval(timer.value);
    }
    timer.value = window.setInterval(() => {
      refresh();
    }, 30_000);
  });

  onBeforeUnmount(() => {
    if (timer.value) {
      clearInterval(timer.value);
      timer.value = null;
    }
  });

  const lastUpdated = computed(() => {
    const stamp = data.value?.generated_at;
    return stamp ? new Date(stamp) : null;
  });

  return {
    data,
    pending,
    error,
    refresh,
    lastUpdated,
  };
}
