<script setup lang="ts">
import type { NodeSnapshot } from "~/types/dashboard";

const props = defineProps<{ snapshot: NodeSnapshot }>();

const variantClass = computed(() => {
  const tone = props.snapshot.state?.variant ?? "warn";
  const mapping: Record<string, string> = {
    ok: "border-emerald-400/30 bg-emerald-500/15 text-emerald-100",
    warn: "border-amber-400/40 bg-amber-500/15 text-amber-100",
    error: "border-rose-400/40 bg-rose-500/15 text-rose-100",
  };
  return mapping[tone] || mapping.warn;
});

const checkedLabel = computed(() => {
  const stamp = props.snapshot.checked_at;
  if (!stamp) {
    return "Awaiting telemetry";
  }
  const date = new Date(stamp);
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
});

const cpuPercent = computed(() => props.snapshot.metrics?.cpu_percent ?? 0);
const memoryPercent = computed(() => props.snapshot.metrics?.memory_percent ?? 0);

const cpuLabel = computed(() => {
  const value = props.snapshot.metrics?.cpu_percent;
  return typeof value === "number" ? value.toFixed(1) : "0.0";
});

const memoryLabel = computed(() => {
  const value = props.snapshot.metrics?.memory_percent;
  return typeof value === "number" ? value.toFixed(1) : "0.0";
});
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex flex-wrap items-center gap-3">
        <div>
          <p class="text-sm uppercase tracking-[0.3em] text-white/50">{{ snapshot.id }}</p>
          <p class="text-lg font-semibold text-white">{{ snapshot.name }}</p>
        </div>
        <span
          class="rounded-full border px-3 py-1 text-xs font-semibold tracking-wide"
          :class="variantClass"
        >
          {{ snapshot.state?.label || "Unknown" }}
        </span>
        <p class="ml-auto text-xs text-white/50">Updated {{ checkedLabel }}</p>
      </div>
    </template>

    <div class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/40">CPU</p>
          <div class="flex items-center justify-between text-sm font-medium">
            <span>{{ cpuLabel }}%</span>
            <span class="text-white/40">load {{ snapshot.metrics?.load }}</span>
          </div>
          <UProgress
            class="mt-2 h-2"
            :value="cpuPercent || 0"
            color="emerald"
          />
        </div>
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/40">Memory</p>
          <div class="flex items-center justify-between text-sm font-medium">
            <span>{{ memoryLabel }}%</span>
            <span class="text-white/40">{{ snapshot.metrics?.memory_summary }}</span>
          </div>
          <UProgress
            class="mt-2 h-2"
            :value="memoryPercent || 0"
            color="cyan"
          />
        </div>
      </div>

      <dl class="grid gap-4 sm:grid-cols-3">
        <div>
          <dt class="text-xs uppercase tracking-[0.3em] text-white/40">Uptime</dt>
          <dd class="text-lg font-semibold">{{ snapshot.metrics?.uptime }}</dd>
        </div>
        <div>
          <dt class="text-xs uppercase tracking-[0.3em] text-white/40">Guests</dt>
          <dd class="text-lg font-semibold">
            {{ snapshot.metrics?.guests.total }}
            <span class="text-sm font-normal text-white/50">
              (KVM {{ snapshot.metrics?.guests.kvm }} · LXC {{ snapshot.metrics?.guests.lxc }})
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-xs uppercase tracking-[0.3em] text-white/40">Node</dt>
          <dd class="text-lg font-semibold">{{ snapshot.meta?.node_name || snapshot.meta?.name }}</dd>
        </div>
      </dl>

      <UAlert
        v-if="snapshot.error"
        color="rose"
        variant="soft"
        icon="i-heroicons-exclamation-triangle"
        title="API warning"
        :description="snapshot.error?.message || 'Authentication or connection issue.'"
      />
    </div>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" :snapshot="snapshot" />
    </template>
  </UCard>
</template>
