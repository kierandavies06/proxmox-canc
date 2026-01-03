<script setup lang="ts">
const config = useRuntimeConfig();
const route = useRoute();

const stage = computed(() => (config.public.releaseStage || "development").toUpperCase());
const docsUrl = computed(() => config.public.apiDocsUrl);

const links = [
  { label: "Status", to: "/" },
  { label: "Control Room", to: "/console" },
];

const isActive = (path: string) => route.path === path;
</script>

<template>
  <div class="relative min-h-screen overflow-hidden bg-slate-950 text-slate-50">
    <div class="aurora-sheen" aria-hidden="true" />
    <div class="noise-surface" aria-hidden="true" />

    <header class="relative z-20 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl">
      <UContainer class="flex flex-wrap items-center gap-4 py-6">
        <NuxtLink to="/" class="font-semibold uppercase tracking-[0.2em] text-xs text-white/80">
          Command & Control
        </NuxtLink>
        <UBadge color="gray" variant="soft" class="ml-1 text-[0.65rem] text-white/70">
          {{ stage }}
        </UBadge>
        <nav class="ml-auto flex items-center gap-1 text-sm">
          <NuxtLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="rounded-full px-4 py-2 font-medium transition"
            :class="[
              isActive(link.to)
                ? 'bg-white text-slate-900'
                : 'text-white/70 hover:text-white',
            ]"
          >
            {{ link.label }}
          </NuxtLink>
        </nav>
        <UButton
          v-if="docsUrl"
          :to="docsUrl"
          target="_blank"
          color="gray"
          variant="soft"
          icon="i-heroicons-book-open"
        >
          API Docs
        </UButton>
      </UContainer>
    </header>

    <main class="relative z-10">
      <UContainer class="py-10">
        <slot />
      </UContainer>
    </main>

    <footer class="relative z-10 border-t border-white/5 bg-black/20 py-6 text-center text-xs text-white/50">
      Command & Control · Fleet observability + automation
    </footer>

    <UNotifications />
  </div>
</template>
