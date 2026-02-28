export const ENDPOINTS = {
  // Scanner
  SCANNER_UNIFIED: '/scanner/unified',
  SCANNER_TARGET: '/scanner/target',
  SCANNER_WALMART: '/scanner/walmart',
  SCANNER_BESTBUY: '/scanner/bestbuy',
  SCANNER_GAMESTOP: '/scanner/gamestop',
  SCANNER_POKECENTER: '/scanner/pokecenter',
  SCANNER_AMAZON: '/scanner/amazon',
  SCANNER_COSTCO: '/scanner/costco',
  SCANNER_TCGPLAYER: '/scanner/tcgplayer',

  // Cards & Sets
  TCG_CARDS: '/api/tcg/cards',
  TCG_SETS: '/api/tcg/sets',

  // Prices
  PRICES_CARD: '/prices/card',
  PRICES_HISTORY: '/prices/history',
  PRICES_GRADED: '/prices/graded',

  // Drops
  DROPS_UPCOMING: '/drops/upcoming',
  DROPS_INTEL: '/drops/intel',
  DROPS_RUMORS: '/drops/rumors',

  // Grading
  GRADER_ANALYZE: '/grader/analyze',

  // AI
  AI_CHAT: '/ai/chat',

  // Market
  MARKET_FLIP: '/market/flip',

  // Tasks/Monitors
  TASKS: '/tasks',
  TASK_GROUPS: '/tasks/groups',

  // Live
  LIVE_STREAM: '/live/stream',
  LIVE_SCANNER_START: '/live/scanner/start',
  LIVE_SCANNER_STOP: '/live/scanner/stop',

  // Auth
  AUTH_DISCORD: '/auth/discord',
  AUTH_CALLBACK: '/auth/discord/callback',
  AUTH_ME: '/auth/me',
} as const
