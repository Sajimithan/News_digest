import React, { type ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
}

const Button: React.FC<ButtonProps> = ({
  variant = 'ghost',
  size = 'md',
  className = '',
  children,
  type = 'button',
  ...rest
}) => (
  <button
    type={type}
    className={[styles.btn, styles[variant], styles[size], className]
      .filter(Boolean)
      .join(' ')}
    {...rest}
  >
    {children}
  </button>
)

export default Button
