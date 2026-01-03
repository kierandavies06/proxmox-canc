export default defineNuxtRouteMiddleware((to) => {
  const config = useRuntimeConfig();
  const requireAuth = config.public.requireAuth;

  if (!requireAuth) {
    return;
  }

  // Placeholder: plug real auth/role checks here once implemented.
  if (!process.server) {
    console.warn(
      "[protected-middleware] Authentication required but not yet implemented.\n" +
        `Attempted route: ${to.fullPath}`,
    );
  }
});
