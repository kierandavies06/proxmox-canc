<script setup lang="ts">
import type { NodeSnapshot } from "~/types/dashboard";

definePageMeta({
  middleware: ["protected"],
});

useSeoMeta({
  title: "Control Room",
  description: "Restricted dashboard with inventory context and wake controls.",
});

const config = useRuntimeConfig();
const toast = useToast();

const { data, pending, error, refresh, lastUpdated } = useDashboardSnapshot();
const {
  data: inventory,
  pending: inventoryPending,
  error: inventoryError,
  refresh: refreshInventory,
} = useNodeInventory();

const nodes = computed<NodeSnapshot[]>(() => data.value?.nodes || []);
const events = computed(() => data.value?.events || []);

const aggregate = computed(() => {
  const items = nodes.value;
  if (!items.length) {
    return { total: 0, online: 0, offline: 0, cpu: 0, memory: 0 };
  }
  const online = items.filter((node) => node.state?.online).length;
  const offline = items.length - online;
  const cpuValues = items
    .map((node) => node.metrics?.cpu_percent)
    .filter((value): value is number => typeof value === "number");
  const memoryValues = items
    .map((node) => node.metrics?.memory_percent)
    .filter((value): value is number => typeof value === "number");
  const avg = (values: number[]) =>
    values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
  return { total: items.length, online, offline, cpu: avg(cpuValues), memory: avg(memoryValues) };
});

const lastUpdatedLabel = computed(() => {
  const stamp = lastUpdated.value;
  return stamp
    ? new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(stamp)
    : "Pending";
});

const baseUrl = computed(() => config.public.apiBaseUrl || config.apiBaseUrl);
const actionPending = ref<string | null>(null);

const wakeNode = async (nodeId: string) => {
  try {
    actionPending.value = nodeId;
    await $fetch(`${baseUrl.value}/api/nodes/${nodeId}/wake`, { method: "POST" });
    toast.add({
      color: "emerald",
      title: `Wake packet queued for ${nodeId}`,
    });
  } catch (wakeError: any) {
    toast.add({
      color: "rose",
      title: `Wake failed for ${nodeId}`,
      description: wakeError?.data?.error || wakeError?.message || "Unexpected error",
    });
  } finally {
    actionPending.value = null;
    refresh();
    refreshInventory();
  }
};
</script>

<template>
  <div class="space-y-10">
    <section class="rounded-3xl border border-white/5 bg-white/3 p-8 shadow-glow">
      <div class="flex flex-wrap items-center gap-6">
        <div>
          <p class="text-xs uppercase tracking-[0.4em] text-white/40">Control Room</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">Operational authority</h1>
          <p class="mt-2 max-w-2xl text-sm text-white/60">
            Full node detail, derived signals, and Wake-on-LAN triggers. Wire in your auth stack to guard this
            surface.
          </p>
        </div>
        <div class="ml-auto grid gap-3 text-center text-sm sm:grid-cols-2">
          <div>
            <p class="text-white/50">Avg CPU</p>
            <p class="text-2xl font-semibold text-white">{{ aggregate.cpu.toFixed(1) }}%</p>
          </div>
          <div>
            <p class="text-white/50">Avg Memory</p>
            <p class="text-2xl font-semibold text-white">{{ aggregate.memory.toFixed(1) }}%</p>
          </div>
        </div>
      </div>
      <div class="mt-6 flex flex-wrap items-center gap-4 text-sm text-white/60">
        <span>{{ aggregate.online }} nodes online / {{ aggregate.offline }} offline</span>
        <span class="text-white/40">·</span>
        <span>Last snapshot {{ lastUpdatedLabel }}</span>
        <UButton
          class="ml-auto"
          color="gray"
          variant="soft"
          icon="i-heroicons-arrow-path"
          :loading="pending"
          @click="refresh"
        >
          Refresh
        </UButton>
      </div>
    </section>

    <section class="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div class="space-y-6">
        <NodeSnapshotCard v-for="snapshot in nodes" :key="snapshot.id" :snapshot="snapshot">
          <template #footer="{ snapshot }">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-xs uppercase tracking-[0.4em] text-white/40">Controls</span>
              <UButton
                color="emerald"
                variant="solid"
                size="xs"
                icon="i-heroicons-bolt"
                :loading="actionPending === snapshot.id"
                @click="wakeNode(snapshot.id)"
              >
                Wake node
              </UButton>
            </div>
          </template>
        </NodeSnapshotCard>
        <p v-if="!pending && !nodes.length" class="text-sm text-white/50">
          No telemetry yet—check the Flask API connection and node credentials.
        </p>
      </div>
      <div class="space-y-6">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-base font-semibold text-white">Event stream</h2>
              <UButton variant="ghost" size="xs" icon="i-heroicons-arrow-path" @click="refresh">
                Pull
              </UButton>
            </div>
          </template>
          <ul class="space-y-4">
            <li
              v-for="event in events"
              :key="event.title + event.timestamp"
              class="rounded-2xl border border-white/5 bg-white/5 p-4"
            >
              <p class="text-sm font-semibold text-white">{{ event.title }}</p>
              <p class="text-xs text-white/60">{{ event.body }}</p>
              <p class="text-[0.65rem] uppercase tracking-[0.3em] text-white/30 mt-2">
                {{ event.clock || event.timestamp }}
              </p>
            </li>
          </ul>
        </UCard>

        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-base font-semibold text-white">Inventory</h2>
              <UButton
                variant="ghost"
                size="xs"
                icon="i-heroicons-arrow-path"
                :loading="inventoryPending"
                @click="refreshInventory"
              >
                Reload
              </UButton>
            </div>
          </template>
          <div v-if="inventoryError" class="py-4">
            <UAlert
              color="rose"
              variant="soft"
              icon="i-heroicons-exclamation-triangle"
              title="Node list unavailable"
              :description="inventoryError.message"
            />
          </div>
          <div v-else class="space-y-4 text-sm">
            <div
              v-for="node in inventory || []"
              :key="node.id"
              class="rounded-2xl border border-white/5 bg-white/2 p-4"
            >
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-white">{{ node.name }}</p>
                  <p class="text-xs text-white/50">{{ node.host }}:{{ node.api_port }}</p>
                </div>
                <UButton
                  size="xs"
                  color="gray"
                  variant="ghost"
                  icon="i-heroicons-bolt"
                  :loading="actionPending === node.id"
                  @click="wakeNode(node.id)"
                >
                  Wake
                </UButton>
              </div>
              <p class="mt-2 text-xs text-white/40">MAC {{ node.mac_address || "—" }}</p>
            </div>
            <p v-if="!inventory?.length" class="text-xs text-white/40">No nodes registered yet.</p>
          </div>
        </UCard>
      </div>
    </section>
  </div>
</template>
