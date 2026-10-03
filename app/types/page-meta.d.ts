declare module '#app' {
  interface PageMeta {
    /** i18n key for this page's breadcrumb segment, e.g. `nav.forms`. */
    breadcrumb?: string
    /**
     * Access (02.auth.global.ts): default = signed-in only · 'guest' = signed-out only
     * (login, signup …) · false = anyone (public forms, workspace-not-found).
     */
    auth?: 'guest' | false
    /**
     * manage.* entry host: true = also served there (login, workspace-not-found);
     * 'only' = manage.* only (signup, find workspace).
     */
    manage?: boolean | 'only'
    /** Public form pages (F10): served on any host (forms.*, workspace hosts); no workspace check. */
    public?: boolean
  }
}

export {}
