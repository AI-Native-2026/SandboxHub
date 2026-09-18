import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: window.location.origin,
  realm: "sandboxhub",
  clientId: "sandboxhub-web",
});

export async function initAuth(): Promise<boolean> {
  try {
    const authed = await keycloak.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    });
    return authed;
  } catch (e) {
    console.error("keycloak init failed", e);
    return false;
  }
}

export function roles(): string[] {
  return (keycloak.tokenParsed as any)?.realm_access?.roles || [];
}

export function hasRole(role: string): boolean {
  return roles().includes(role);
}

export function canWrite(): boolean {
  return roles().some((r) => ["platform-admin", "tenant-admin", "developer"].includes(r));
}
