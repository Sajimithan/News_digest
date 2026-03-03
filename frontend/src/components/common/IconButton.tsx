import React, { type ButtonHTMLAttributes } from 'react'
import styles from './IconButton.module.css'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary'
  active?: boolean
}

const IconButton: React.FC<IconButtonProps> = ({
  variant = 'default',
  active = false,
  className = '',
  children,
  type = 'button',
  ...rest
}) => (
  <button
    type={type}
    className={[
      styles.btn,
      styles[variant],
      active ? styles.active : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')}
    {...rest}
  >
    {children}
  </button>
)

export default IconButton
