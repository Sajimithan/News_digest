import React from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './NotFoundPage.module.css'

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <div className={styles.code}>404</div>
      <p className={styles.msg}>Page not found</p>
      <button className={styles.btn} onClick={() => navigate('/')}>
        ← Back to Chat
      </button>
    </div>
  )
}

export default NotFoundPage
