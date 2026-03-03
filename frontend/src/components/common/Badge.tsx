import React from 'react'
import styles from './Badge.module.css'

interface BadgeProps {
  label: string
  variant?: 'live' | 'info' | 'success' | 'error'
  pulse?: boolean
}

const Badge: React.FC<BadgeProps> = ({ label, variant = 'live', pulse = false }) => (
  <span
    className={[styles.badge, styles[variant], pulse ? styles.pulse : '']
      .filter(Boolean)
      .join(' ')}
  >
    {label}
  </span>
)

export default Badge
