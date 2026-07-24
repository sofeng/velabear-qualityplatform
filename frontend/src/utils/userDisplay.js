export const getUserFullName = (user) => {
  if (!user) {
    return ''
  }

  const fullName = String(user.full_name || '').trim()
  if (fullName) {
    return fullName
  }

  const firstName = String(user.first_name || '').trim()
  const lastName = String(user.last_name || '').trim()
  return `${firstName}${lastName}`.trim()
}

export const getUserDisplayName = (user, fallback = '') => {
  return (
    getUserFullName(user) ||
    String(user?.username || '').trim() ||
    String(user?.email || '').trim() ||
    fallback
  )
}
