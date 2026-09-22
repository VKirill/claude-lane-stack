import type { On, PluginOptions, Register } from 'claude-code'

import { register as registerCompact } from './fast-jev.js'
import { register as registerRouter } from './jev-router.js'
import { register as registerWinnow } from './winnow.js'

/** One function-hook module per plugin. Compact, winnow and jev-router register here. */
export const register: Register = (on: On, options: PluginOptions) => {
  registerCompact(on, options)
  registerWinnow(on, options)
  registerRouter(on, options)
}
