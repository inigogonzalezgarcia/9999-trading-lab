/** Build-time switches for the public static site (Cloudflare Pages) versus the local research tool. */
export const STATIC_MODE: boolean = (import.meta.env.VITE_STATIC_MODE as string | undefined) === '1';
export const BASE_URL: string = import.meta.env.BASE_URL || '/';
export const DATA_BASE: string = `${BASE_URL}data/`;
export const TURNSTILE_SITE_KEY: string = (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) ?? '';
export const REPO_URL = 'https://github.com/inigogonzalezgarcia/9999-trading-lab';
export const AUTHOR_SITE = 'https://inigogonzalezgarcia.github.io';
export const CONTACT_URL = 'https://inigogonzalezgarcia.github.io/about.html#contacto';
export const LINKEDIN_URL = 'https://www.linkedin.com/in/inigogonzalezgarcia/';
export const SITE_NAME = 'FX Research Lab';
/** Paid kit (Gumroad handles checkout, VAT and delivery). The site only links to it. */
export const KIT_URL = 'https://fxresearchlab.gumroad.com/l/kit-backtest';
export const KIT_PRICE = '19 €';
