/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_DEFAULT_PROVIDER: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
