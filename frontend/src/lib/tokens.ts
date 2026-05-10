/**
 * Numeric design tokens for use in inline styles.
 * CSS variable values (strings) cannot be used for numeric style properties
 * like fontWeight, so we keep the numeric equivalents here.
 */
export const fontWeight = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const
