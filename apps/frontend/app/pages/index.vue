<script setup lang="ts">
import type { DashboardEvent, NodeSnapshot } from "~/types/dashboard";

const config = useRuntimeConfig();
const requireAuth = computed(() => config.public.requireAuth);

useSeoMeta({
  title: "Status",
  description: "Live resource posture and telemetry pulled from the Flask API.",
});

const { data, pending, error, refresh, lastUpdated } = useDashboardSnapshot();

const nodes = computed<NodeSnapshot[]>(() => data.value?.nodes || []);
const events = computed<DashboardEvent[]>(() => data.value?.events || []);

const aggregate = computed(() => {
  const items = nodes.value;
  if (!items.length) {
    return {
      total: 0,
      online: 0,
      offline: 0,
      cpu: 0,
      memory: 0,
    };
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

  return {
    total: items.length,
    online,
    offline,
    cpu: avg(cpuValues),
    memory: avg(memoryValues),
  };
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

const eventToneIcon: Record<string, string> = {
  info: "i-heroicons-information-circle",
  warn: "i-heroicons-exclamation-triangle",
  danger: "i-heroicons-bolt",
};

</script>

<template>
  <div class="space-y-10">
    <section class="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
      <div class="rounded-3xl border border-white/5 bg-linear-to-br from-slate-900/80 via-slate-900/50 to-emerald-950/40 p-8 shadow-glow">
        <p class="text-xs uppercase tracking-[0.4em] text-white/40">Command & Control</p>
        <h1 class="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl">
          Fleet status, performance, and wake triggers in one pane of glass.
        </h1>
        <p class="mt-4 max-w-2xl text-base text-white/70">
          The public view surfaces live uptime, CPU pressure, and derived events from the Flask API.
          Restricted controls stay tucked behind the Control Room.
        </p>
        <div class="mt-6 flex flex-wrap gap-4">
          <UButton
            color="gray"
            variant="solid"
            size="lg"
            icon="i-heroicons-arrow-path"
            :loading="pending"
            @click="refresh"
          >
            Refresh Snapshot
          </UButton>
          <UButton
            to="/console"
            size="lg"
            color="emerald"
            variant="soft"
            icon="i-heroicons-lock-closed"
          >
            Control Room
          </UButton>
        </div>
        <p class="mt-4 text-xs text-white/40">Last updated · {{ lastUpdatedLabel }}</p>
      </div>
      <div class="space-y-4">
        <div class="rounded-3xl border border-white/5 bg-white/2 p-6">
          <p class="text-xs uppercase tracking-[0.4em] text-white/40">Fleet posture</p>
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p class="text-sm text-white/60">Online</p>
              <p class="text-3xl font-semibold text-white">{{ aggregate.online }}</p>
            </div>
            <div>
              <p class="text-sm text-white/60">Offline</p>
              <p class="text-3xl font-semibold text-white">{{ aggregate.offline }}</p>
            </div>
            <div>
              <p class="text-sm text-white/60">Avg CPU</p>
              <p class="text-3xl font-semibold text-white">{{ aggregate.cpu.toFixed(1) }}%</p>
            </div>
            <div>
              <p class="text-sm text-white/60">Avg Memory</p>
              <p class="text-3xl font-semibold text-white">{{ aggregate.memory.toFixed(1) }}%</p>
            </div>
          </div>
        </div>
        <UAlert
          v-if="requireAuth"
          color="emerald"
          icon="i-heroicons-adjustments-horizontal"
          title="Control Room guarded"
          description="Auth gating is enabled. Only public telemetry is exposed on this screen."
        />
      </div>
    </section>

    <section>
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-lg font-semibold text-white">Nodes</h2>
        <UButton variant="ghost" icon="i-heroicons-arrow-path" :loading="pending" @click="refresh">
          Sync
        </UButton>
      </div>
      <div v-if="error" class="mt-4">
        <UAlert
          color="rose"
          variant="soft"
          icon="i-heroicons-exclamation-triangle"
          title="API unavailable"
          :description="error.message || 'Unable to reach the Flask API.'"
        />
      </div>
      <div v-else class="mt-6 grid gap-6 lg:grid-cols-2">
        <template v-if="pending && !nodes.length">
          <USkeleton class="h-64 rounded-3xl border border-white/5 bg-white/5" />
          <USkeleton class="h-64 rounded-3xl border border-white/5 bg-white/5" />
        </template>
        <template v-else>
          <NodeSnapshotCard v-for="snapshot in nodes" :key="snapshot.id" :snapshot="snapshot" />
        </template>
        <p v-if="!pending && !nodes.length" class="text-sm text-white/50">
          No nodes reported by the API yet. Configure nodes in the Flask service to populate this view.
        </p>
      </div>
    </section>

    <section class="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold text-white">Recent events</h3>
            <span class="text-xs text-white/40">{{ events.length }} tracked</span>
          </div>
        </template>
        <ul class="space-y-4">
          <li
            v-for="event in events"
            :key="event.title + event.timestamp"
            class="rounded-2xl border border-white/5 bg-white/2 p-4"
          >
            <div class="flex items-center gap-3">
              <div class="rounded-full border border-white/10 bg-white/5 p-2">
                <UIcon :name="eventToneIcon[event.tone] || eventToneIcon.info" />
              </div>
              <div>
                <p class="text-sm font-semibold text-white">{{ event.title }}</p>
                <p class="text-xs text-white/50">
                  {{ event.body }}
                  <span v-if="event.clock" class="text-white/30">· {{ event.clock }}</span>
                </p>
              </div>
            </div>
          </li>
        </ul>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold text-white">API links</h3>
            <span class="text-xs text-white/40">Public surface</span>
          </div>
        </template>
        <div class="space-y-4 text-sm text-white/70">
          <p>Use the documented Flask endpoints to wire this telemetry into other systems.</p>
          <div class="rounded-2xl border border-white/5 bg-white/2 p-4">
            <p class="text-xs uppercase tracking-[0.4em] text-white/40">Dashboard JSON</p>
            <p class="mt-1 font-semibold text-white">{{ config.public.apiBaseUrl || config.apiBaseUrl }}/api/dashboard</p>
          </div>
          <div class="rounded-2xl border border-white/5 bg-white/2 p-4">
            <p class="text-xs uppercase tracking-[0.4em] text-white/40">OpenAPI</p>
            <NuxtLink
              :to="config.public.apiDocsUrl"
              class="mt-1 inline-flex items-center gap-2 font-semibold text-emerald-300 hover:text-emerald-200"
            >
              {{ config.public.apiDocsUrl }}
              <UIcon name="i-heroicons-arrow-up-right" />
            </NuxtLink>
          </div>
        </div>
      </UCard>
    </section>
  </div>
</template>
